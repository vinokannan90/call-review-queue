# Changelog

All notable changes to the Call Review Queue system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2026-03-09

### Added
- **Admin Timer Reset Controls**: Reset buttons next to working and break timers on admin dashboard
- **Clock-Out Time Display**: Shows when team members completed their shift
- **Timer Freeze After Sign-Off**: Timers display final frozen values instead of disappearing
- **Reset Timer Route**: New POST endpoint `/admin/reset_timer/<member_id>/<timer_type>` for admin control

### Fixed
- **Timer Visibility Bug**: Time tracking section now persists after team member signs off
- **CSS Linter Errors**: Changed admin_reports.html display logic from inline Jinja style to Bootstrap classes
- **Unused Import**: Removed unused `sqlalchemy.func` import from app.py

### Changed
- **JavaScript Timer Logic**: Now checks clock-out time to freeze timer updates when shift ends
- **Admin Dashboard Display**: Removed `status != 'offline'` condition from attendance display
- **Reset Confirmation**: Added confirmation prompt before executing timer resets

### Security
- Rate limiting applied to reset timer endpoint (30 requests per 60 seconds)
- Admin role authorization required for all reset operations

---

## [0.2.0] - 2026-03-09

### Added
- **Manual CallerID Assignment via Drag & Drop**: Admin can now manually assign up to 3 CallerIDs per team member by dragging from queue to team member cards
- **QA Role CallerID Submission**: QA users can now submit CallerIDs directly through their dashboard
- **Reserved Queue for Team Members**: Complaint team members can see their personally reserved CallerIDs in priority order
- **Database Schema for Manual Assignments**: New fields `reserved_for_member_id`, `reserved_at`, and `reserved_by_id` in CallerID model
- **QA User in Demo Data**: Added `qa.user` account to seed data for testing
- **Database Reset Utility**: Created `reset_db.py` script for easy database schema updates

### Changed
- **Auto-Assignment Priority Logic**: System now prioritizes manually reserved CallerIDs before general FIFO queue
- **Sign-Off Behavior**: Returns all reserved CallerIDs to general queue when team member signs off
- **QA Dashboard Enhancement**: Added CallerID submission form and statistics display
- **Admin Dashboard UI**: Enhanced with drag-and-drop zones, reservation indicators, and real-time visual feedback

### Fixed
- **Auto-Refresh Issue**: Removed meta refresh tags from all dashboards that were causing form inputs to disappear
- **SQLAlchemy Relationship Ambiguity**: Explicitly specified foreign_keys to resolve multiple foreign key path conflicts
- **Database Constraint Errors**: Fixed relationship definitions between User and CallerID models

### Technical Details
- **Database Migration Required**: New columns added to `caller_ids` table
- **Backward Compatibility**: ⚠️ Breaking change - existing database must be reset and reseeded
- **Browser Compatibility**: Drag-and-drop requires modern browser with HTML5 support

### Security
- Manual assignment operations restricted to Admin role only
- Proper authorization checks on all new API endpoints

---

## [0.1.0] - Initial PoC (Pre-release)

### Added
- Initial proof-of-concept implementation
- Basic CallerID queue management
- Team member approval workflow
- Auto-assignment functionality
- User, Admin, Complaint, and QA role scaffolding
