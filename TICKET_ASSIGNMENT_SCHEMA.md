# Support Ticket Assignment & Escalation System - Schema Design

## Overview
This document outlines the database schema design for managing support ticket assignments and escalations through a hierarchical organizational structure.

## New Tables Created

### 1. **ticket_assignments**
Tracks all assignments of tickets to team members. Every time a ticket is assigned, reassigned, or escalated, a new record is created.

**Columns:**
- `id` (UUID, PK): Unique identifier
- `ticket_id` (UUID, FK): Reference to the ticket
- `assigned_to_user_id` (UUID, FK): The user currently responsible for the ticket
- `assigned_by_user_id` (UUID, FK, nullable): Who made the assignment
- `assignment_type` (String): Type of assignment
  - `assigned`: Initial assignment to an employee
  - `escalated`: Moved up the hierarchy
  - `reassigned`: Reassigned to someone at the same level
  - `completed`: Ticket was resolved
- `is_current` (Boolean): Indicates if this is the active assignment
- `assigned_at` (String): When the assignment was made
- `completed_at` (String, nullable): When the ticket was completed
- `notes` (Text, nullable): Optional notes about the assignment
- `created_at, updated_at` (String): Timestamps

**Indexes:**
- `idx_ticket_assignments_ticket_id`: For finding all assignments for a ticket
- `idx_ticket_assignments_assigned_to`: For finding assignments for a user
- `idx_ticket_assignments_is_current`: For quickly finding current assignments

**Usage Pattern:**
```sql
-- Get current assignment for a ticket
SELECT * FROM ticket_assignments 
WHERE ticket_id = '...' AND is_current = true;

-- Get all tickets assigned to a user
SELECT * FROM ticket_assignments 
WHERE assigned_to_user_id = '...' AND is_current = true;

-- Get history of a ticket
SELECT * FROM ticket_assignments 
WHERE ticket_id = '...' 
ORDER BY assigned_at DESC;
```

### 2. **ticket_escalations**
Specifically tracks escalations as tickets move up the management hierarchy. Separate from assignments for better audit tracking.

**Columns:**
- `id` (UUID, PK): Unique identifier
- `ticket_id` (UUID, FK): Reference to the ticket
- `escalated_from_user_id` (UUID, FK): Who escalated it (usually the person who couldn't resolve it)
- `escalated_to_user_id` (UUID, FK): Who received the escalation (usually their manager)
- `escalation_level` (Integer): Level in the hierarchy
  - 0 = Employee
  - 1 = Manager
  - 2 = Senior Manager
  - 3 = Director
  - 4 = Admin
- `reason` (Text, nullable): Why was it escalated
- `escalated_at` (String): When the escalation happened
- `created_at` (String): Record creation timestamp

**Usage Pattern:**
```sql
-- Get escalation history for a ticket
SELECT * FROM ticket_escalations 
WHERE ticket_id = '...' 
ORDER BY escalated_at DESC;

-- Get the last escalation
SELECT * FROM ticket_escalations 
WHERE ticket_id = '...' 
ORDER BY escalated_at DESC LIMIT 1;

-- Track escalations by user
SELECT * FROM ticket_escalations 
WHERE escalated_from_user_id = '...';
```

## Workflow Examples

### Example 1: Initial Assignment
```
1. Customer creates ticket (status: QUEUED)
2. Admin assigns to Employee Jessica (assignment_type: assigned, is_current: true)
3. Ticket status updated to ASSIGNED
```

**Database State:**
```
Ticket:
  id: ticket-123
  status: assigned
  
TicketAssignment:
  id: assign-001
  ticket_id: ticket-123
  assigned_to_user_id: jessica-id
  assignment_type: assigned
  is_current: true
  assigned_at: 2026-02-14 10:00:00
```

### Example 2: Ticket Escalation (Not Resolved)
```
1. Jessica works on ticket but can't resolve it
2. Jessica escalates to her manager John
3. System closes Jessica's assignment and creates new one for John
4. Escalation record created for audit trail
```

**Database State After Escalation:**
```
TicketAssignment (Jessica's - now closed):
  id: assign-001
  is_current: false
  completed_at: null  (not resolved, just escalated)

TicketAssignment (John's - new):
  id: assign-002
  ticket_id: ticket-123
  assigned_to_user_id: john-id
  assignment_type: escalated
  is_current: true
  assigned_at: 2026-02-14 11:30:00

TicketEscalation (Audit trail):
  id: escalation-001
  ticket_id: ticket-123
  escalated_from_user_id: jessica-id
  escalated_to_user_id: john-id
  escalation_level: 1  (manager level)
  reason: "Unable to resolve - requires manager review"
  escalated_at: 2026-02-14 11:30:00
```

### Example 3: Further Escalation
```
1. John works on ticket but also can't resolve it
2. John escalates to his manager Alex
3. Another escalation record created
```

**Database State:**
```
TicketEscalation Records (showing escalation chain):
  1. jessica → john (level 1, employee to manager)
  2. john → alex (level 2, manager to senior manager)
```

### Example 4: Ticket Resolved
```
1. Alex resolves the ticket
2. Current assignment closed with completed_at timestamp
3. Ticket status updated to DONE
```

**Database State:**
```
TicketAssignment (Alex's - now completed):
  id: assign-003
  is_current: false
  completed_at: 2026-02-14 14:00:00
```

## Organization Hierarchy

Your hierarchy structure:
```
Admin
  └── Manager (Alex)
      └── Manager (John)  
          └── Employee (Jessica)
```

Each user has a `manager_id` pointing to their direct manager. The system uses this to determine escalation paths.

## Key Features

1. **Assignment Tracking**: Know who has the ticket and when it was assigned
2. **Escalation History**: Full audit trail of escalations with reasons
3. **Current Assignment**: Quick query to find who's working on a ticket now
4. **User Workload**: Query all current assignments for a user
5. **Escalation Path**: Trace the entire escalation journey of a ticket

## CRUD Operations Available

### Assignment Operations
- `create_ticket_assignment()`: Create new assignment
- `get_current_assignment()`: Get active assignment for a ticket
- `get_assignments_by_ticket()`: Get all assignments (history)
- `get_assignments_by_user()`: Get user's assignments
- `update_assignment()`: Update an assignment
- `close_current_assignment()`: Close assignment (escalation/completion)
- `reassign_ticket()`: Reassign ticket (close old, create new)

### Escalation Operations
- `create_ticket_escalation()`: Record an escalation
- `get_escalations_by_ticket()`: Get escalation history
- `get_last_escalation()`: Get most recent escalation

## Database Relationships

```
User (1) ──── (Many) TicketAssignment (assigned_to_user_id)
User (1) ──── (Many) TicketAssignment (assigned_by_user_id)
Ticket (1) ──── (Many) TicketAssignment
Ticket (1) ──── (Many) TicketEscalation

User (1) ──── (Many) TicketEscalation (escalated_from_user_id)
User (1) ──── (Many) TicketEscalation (escalated_to_user_id)
```

## Migration
Run: `alembic upgrade head`

This will create both tables with proper foreign keys and indexes.
