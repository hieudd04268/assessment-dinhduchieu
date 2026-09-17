# Technical Specification: Todo Sharing

> Users should be able to share their todo list with other users with either read-only (viewer) or edit (editor) permissions, and owners can revoke access anytime.

## 1. Overview & Objective

**Feature Summary**: Allow todo list owners to invite other users to collaborate on their todo lists with two permission levels: **Viewer** (read-only) and **Editor** (read + write). Owners retain full control and can revoke access at any time.

**Problem Statement**: Currently todos are strictly private per user. Users need to collaborate on shared projects/tasks without sharing credentials.

**Target Audience / Roles**:
- **Owner**: Todo creator, full CRUD + share/revoke permissions
- **Editor**: Invited user with read + write access (create, update, delete todos in shared list)
- **Viewer**: Invited user with read-only access (list, view todos only)

## 2. User Stories & Acceptance Criteria

### User Story 1: Owner invites a collaborator
- **As a** Owner
- **I want to** invite another user by email with Viewer or Editor role
- **So that** they can collaborate on my todo list
- **Acceptance Criteria**:
  - [ ] Owner can invite any registered user by email
  - [ ] Owner selects permission: `viewer` or `editor`
  - [ ] Invitation creates a share record immediately
  - [ ] Invited user sees shared todos in their list (filtered by `shared=true`)
  - [ ] Duplicate invite to same user returns 409 Conflict
  - [ ] Self-sharing (inviting own email) returns 400 Bad Request

### User Story 2: Editor modifies shared todos
- **As an** Editor
- **I want to** create, update, delete todos in a shared list
- **So that** I can contribute to the project
- **Acceptance Criteria**:
  - [ ] Editor can POST /todos (creates todo owned by list owner)
  - [ ] Editor can PUT /todos/{id} for todos in shared list
  - [ ] Editor can DELETE /todos/{id} for todos in shared list
  - [ ] Editor CANNOT share/revoke permissions
  - [ ] Editor CANNOT invite other users

### User Story 3: Viewer reads shared todos
- **As a** Viewer
- **I want to** view todos in a shared list
- **So that** I can stay informed without modifying
- **Acceptance Criteria**:
  - [ ] Viewer can GET /todos (includes shared todos)
  - [ ] Viewer can GET /todos/{id} for shared todos
  - [ ] Viewer GET /todos?shared_only=true returns only shared
  - [ ] Viewer POST/PUT/DELETE returns 403 Forbidden

### User Story 4: Owner revokes access
- **As an** Owner
- **I want to** revoke a user's access to my todo list
- **So that** they can no longer view or edit
- **Acceptance Criteria**:
  - [ ] Owner DELETE /shares/{user_id} revokes immediately
  - [ ] Revoked user loses access instantly (cache invalidated)
  - [ ] Revoked user's pending requests fail with 403
  - [ ] Owner cannot revoke own access (self-revocation prevented)

### User Story 5: Owner views and manages collaborators
- **As an** Owner
- **I want to** see all collaborators and their roles
- **So that** I can manage permissions
- **Acceptance Criteria**:
  - [ ] GET /shares returns list of {user_id, email, role, created_at}
  - [ ] PATCH /shares/{user_id} changes role (viewer ↔ editor)
  - [ ] Role change takes effect immediately

## 3. Scope

**In-Scope**:
- Share todo list with registered users by email
- Two permission levels: viewer, editor
- Owner manages invites, role changes, revocation
- Immediate cache invalidation on permission changes
- Cross-user authorization enforcement

**Out-of-Scope**:
- Public share links (anyone with link)
- Groups/teams (only individual user invites)
- Transfer ownership
- Comments/mentions on todos
- Notification emails (assume in-app notification only)
- Nested sharing (editor cannot re-share)
- Bulk invite / CSV import

## 4. Database Design

### New Tables

#### `todo_shares`
```sql
CREATE TABLE todo_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('viewer', 'editor')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (owner_id, user_id)
);
```

**Constraints**:
- `UNIQUE (owner_id, user_id)` — One share per owner-user pair
- `CHECK (role IN ('viewer', 'editor'))` — Only valid roles
- `ON DELETE CASCADE` — Auto-cleanup when user deleted

**Indexes**:
```sql
-- For "list my shared todos" queries
CREATE INDEX idx_todo_shares_user_id ON todo_shares(user_id);
-- For "list collaborators of my list" queries
CREATE INDEX idx_todo_shares_owner_id ON todo_shares(owner_id);
-- For permission checks during todo access
CREATE INDEX idx_todo_shares_owner_user ON todo_shares(owner_id, user_id);
```

### Modified Queries

**Todo list query** (for user U):
```sql
SELECT t.* FROM todos t
WHERE t.user_id = :user_id                    -- Own todos
   OR EXISTS (
       SELECT 1 FROM todo_shares ts
       WHERE ts.owner_id = t.user_id
         AND ts.user_id = :user_id
   )
ORDER BY t.created_at DESC, t.id DESC;
```

**Todo access check** (for user U accessing todo T):
```sql
SELECT 1 FROM todos t
LEFT JOIN todo_shares ts ON ts.owner_id = t.user_id AND ts.user_id = :user_id
WHERE t.id = :todo_id
  AND (t.user_id = :user_id OR ts.role IN ('viewer', 'editor'));
```

## 5. API Contracts & Endpoints

### Share Management

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/api/v1/todos/shares` | Invite user to todo list | Owner |
| GET | `/api/v1/todos/shares` | List collaborators | Owner |
| PATCH | `/api/v1/todos/shares/{user_id}` | Update collaborator role | Owner |
| DELETE | `/api/v1/todos/shares/{user_id}` | Revoke collaborator access | Owner |

### Request/Response Schemas

**POST /api/v1/todos/shares** — Invite collaborator
```json
// Request
{
  "email": "collaborator@example.com",
  "role": "editor"  // "viewer" | "editor"
}

// Response 201
{
  "id": "uuid",
  "owner_id": "uuid",
  "user_id": "uuid",
  "user_email": "collaborator@example.com",
  "role": "editor",
  "created_at": "2026-09-16T10:00:00Z",
  "updated_at": "2026-09-16T10:00:00Z"
}

// Errors
// 400: Self-sharing attempt
// 404: User not found
// 409: Already shared with this user
// 422: Invalid role
```

**GET /api/v1/todos/shares** — List collaborators
```json
// Response 200
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "user_email": "collab1@example.com",
    "role": "editor",
    "created_at": "2026-09-16T10:00:00Z"
  },
  {
    "id": "uuid",
    "user_id": "uuid",
    "user_email": "collab2@example.com",
    "role": "viewer",
    "created_at": "2026-09-16T11:00:00Z"
  }
]
```

**PATCH /api/v1/todos/shares/{user_id}** — Change role
```json
// Request
{
  "role": "viewer"  // "viewer" | "editor"
}

// Response 200
{
  "id": "uuid",
  "owner_id": "uuid",
  "user_id": "uuid",
  "user_email": "collaborator@example.com",
  "role": "viewer",
  "created_at": "2026-09-16T10:00:00Z",
  "updated_at": "2026-09-16T12:00:00Z"
}

// Errors
// 403: Not owner
// 404: Share not found
// 422: Invalid role
```

**DELETE /api/v1/todos/shares/{user_id}** — Revoke access
```json
// Response 204 No Content

// Errors
// 403: Not owner or self-revocation attempt
// 404: Share not found
```

### Modified Todo Endpoints (Authorization)

**GET /api/v1/todos** — Enhanced with shared todos
```
Query params:
- shared_only: boolean (default false) — only return shared todos
- page, size: pagination

Authorization:
- Returns todos WHERE user_id = current_user OR shared with current_user
- For shared todos: include owner_email field
```

**GET /api/v1/todos/{id}** — Access check includes shares
```
Authorization:
- 200 if owner OR has share (viewer/editor)
- 404 if not found OR no access
```

**POST /api/v1/todos** — Create in shared list (editor only)
```
Authorization:
- If todo.user_id != current_user: must have editor share on that owner's list
- Created todo has owner_id = list owner
```

**PUT /api/v1/todos/{id}** — Update shared todo (editor only)
```
Authorization:
- 200 if owner OR editor share
- 403 if viewer share
- 404 if no access
```

**DELETE /api/v1/todos/{id}** — Delete shared todo (editor only)
```
Authorization:
- 200 if owner OR editor share
- 403 if viewer share
- 404 if no access
```

### Error Payload Format
```json
{
  "detail": "Human-readable error message",
  "error_code": "SHARE_NOT_FOUND | SELF_SHARE_FORBIDDEN | DUPLICATE_SHARE | INSUFFICIENT_PERMISSION | ROLE_INVALID"
}
```

## 6. Business Logic & Security Considerations

### Authorization & Permission Matrix

| Action | Owner | Editor | Viewer | Other |
|---|---|---|---|---|
| List todos (own + shared) | ✅ | ✅ (own + shared) | ✅ (own + shared) | ❌ |
| View shared todo detail | ✅ | ✅ | ✅ | ❌ |
| Create todo in shared list | ✅ | ✅ (owner's list) | ❌ | ❌ |
| Update shared todo | ✅ | ✅ | ❌ | ❌ |
| Delete shared todo | ✅ | ✅ | ❌ | ❌ |
| Invite collaborator | ✅ | ❌ | ❌ | ❌ |
| List collaborators | ✅ | ❌ | ❌ | ❌ |
| Change collaborator role | ✅ | ❌ | ❌ | ❌ |
| Revoke collaborator | ✅ | ❌ | ❌ | ❌ |

### Edge Cases & Race Conditions

| Scenario | Handling |
|---|---|
| **Self-sharing** | Reject at API layer (400) before DB insert |
| **Duplicate invite** | DB unique constraint → catch IntegrityError → 409 |
| **Invite non-existent user** | Check user exists first → 404 |
| **Concurrent role change + todo edit** | Use SELECT FOR UPDATE on share row during permission check; cache invalidated after role change |
| **Owner revokes during Editor's request** | Middleware checks share on each request; revoked → 403 |
| **Editor tries to invite** | 403 at authorization layer |
| **Viewer tries to edit** | 403 at authorization layer (check role before mutation) |
| **Owner deletes account** | CASCADE DELETE on todo_shares cleans up automatically |
| **Collaborator deletes account** | CASCADE DELETE removes their shares |
| **Shared todo list gets very large** | Pagination applies to combined (own + shared) results; indexes on todo_shares optimize JOIN |

### Immediate Cache Invalidation
- On **share create/update/delete**: Invalidate `todos:list:{user_id}:*` for both owner AND collaborator
- On **todo create/update/delete by editor**: Invalidate cache for owner AND all collaborators with access
- Use Redis pub/sub or direct invalidation in same transaction

## 7. Caching & Invalidation Strategy

### Cache Key Structure
```
# Own todo lists (unchanged)
todos:list:{user_id}:{page}:{size}

# Shared todo lists (NEW - includes shared)
todos:list:{user_id}:{page}:{size}:shared:{true|false}
```

### Invalidation Triggers
| Event | Keys to Invalidate |
|---|---|
| Owner creates share | `todos:list:{owner_id}:*`, `todos:list:{collab_id}:*` |
| Owner updates role | `todos:list:{owner_id}:*`, `todos:list:{collab_id}:*` |
| Owner revokes share | `todos:list:{owner_id}:*`, `todos:list:{collab_id}:*` |
| Owner creates/updates/deletes own todo | `todos:list:{owner_id}:*` + all collaborator keys |
| Editor creates/updates/deletes shared todo | `todos:list:{owner_id}:*` + all collaborator keys |
| Viewer accesses (read-only) | No invalidation needed |

### Implementation Notes
- Maintain a Redis SET `todo:collaborators:{owner_id}` = {user_id1, user_id2, ...} for efficient bulk invalidation
- On share create: `SADD todo:collaborators:{owner_id} {collab_id}`
- On share delete: `SREM todo:collaborators:{owner_id} {collab_id}`
- Invalidation: `SMEMBERS todo:collaborators:{owner_id}` → iterate + delete pattern keys

## 8. Migration Strategy
1. Create `todo_shares` table via Alembic migration
2. Add indexes concurrently (PostgreSQL `CREATE INDEX CONCURRENTLY`)
3. Deploy API with feature flag disabled
4. Enable feature flag after verification
5. No data migration needed (empty table initially)

## 9. Testing Strategy
- Unit: Share CRUD, permission matrix, edge cases
- Integration: Full flow (invite → editor creates → viewer reads → owner revokes)
- E2E: Cross-browser collaboration simulation
- Load: Concurrent permission changes + todo mutations