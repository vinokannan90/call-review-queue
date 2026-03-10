# Release Notes - v0.2.0

**Release Date**: March 9, 2026  
**Release Type**: PoC Enhancement Release

## 🎯 Overview

This enhanced PoC release introduces **Manual CallerID Assignment** capabilities, empowering administrators with flexible queue management through an intuitive drag-and-drop interface. Additionally, QA team members gain the ability to submit CallerIDs directly, streamlining the review workflow.

## 🚀 Key Features

### 1. Manual CallerID Assignment (Drag & Drop)
Administrators can now manually assign CallerIDs to specific team members:
- **Drag CallerIDs** from the pending queue onto team member cards
- **Reserve up to 3 CallerIDs** per team member
- **Visual indicators** show reservation status and count
- **Priority handling**: Manually assigned CallerIDs take precedence over FIFO queue
- **Flexible removal**: Click X on reserved badges to unreserve

**Use Cases**:
- Assign complex cases to experienced team members
- Balance workload across the team
- Pre-assign CallerIDs to members on break who will return soon

### 2. QA Role Enhancement
QA users can now submit CallerIDs for review:
- Full submission form with CallerID, AWS URL, and reason fields
- View submission history and statistics
- No more page auto-refresh interrupting form input

### 3. Reserved Queue Visibility
Complaint team members see their personal queue:
- View all CallerIDs manually assigned to them
- See position in queue and submission details
- Preview recording links before receiving assignment

## 📋 What's Changed

### For Administrators
- New drag-and-drop interface in Team Availability section
- Reserved CallerIDs display under each team member (X/3)
- Enhanced pending queue with reservation column
- Ability to unreserve CallerIDs with one click

### For Complaint Team Members
- New "My Reserved Queue" section on dashboard
- Automatically receive reserved CallerIDs first
- Reservations cleared when signing off (returned to general queue)

### For QA Team
- New CallerID submission form
- Submission statistics and history
- No more auto-refresh disruption

## ⚠️ Breaking Changes

### Database Schema Changes
**Action Required**: Database must be reset and reseeded

New columns added to `caller_ids` table:
- `reserved_for_member_id` (nullable FK to team_members)
- `reserved_at` (nullable datetime)
- `reserved_by_id` (nullable FK to users)

### Migration Steps
```powershell
# Backup existing data if needed
# Then reset database
python reset_db.py

# Reseed with demo data
python seed.py
```

## 🔧 Technical Improvements

- Fixed SQLAlchemy relationship ambiguity errors
- Removed problematic auto-refresh meta tags
- Enhanced error handling for manual assignment operations
- Added proper foreign key constraints
- Improved API response structure with success/error messages

## 📚 Documentation Updates

- Updated README with new feature descriptions
- Added CHANGELOG.md following Keep a Changelog format
- Created VERSION file for release tracking
- Added comprehensive inline code documentation

## 🐛 Bug Fixes

- Fixed form input disappearing due to page auto-refresh
- Resolved database relationship ambiguity causing startup crashes
- Fixed sign-off behavior to properly clear reservations

## 🔐 Security

- Manual assignment operations restricted to Admin role
- Proper authorization checks on new API endpoints
- Form validation for all submission endpoints

## 📦 New Files

- `reset_db.py` - Database schema reset utility
- `VERSION` - Version tracking file
- `CHANGELOG.md` - Change history documentation
- `RELEASE-NOTES.md` - This file

## 🎓 Training & Adoption

### For Administrators
1. Review "Manual Assignment" section in updated documentation
2. Practice drag-and-drop in test environment
3. Understand 3-CallerID limit per member

### For Complaint Team
1. Check "My Reserved Queue" section when logging in
2. Understand priority: reserved → general queue
3. Remember: signing off clears your reservations

### For QA Team
1. Use new submission form on QA dashboard
2. CallerIDs submitted go to general queue for complaint team

## 🔮 Future Enhancements

Planned for future releases:
- Bulk assignment operations
- Assignment history and analytics
- Configurable reservation limits per role
- Email notifications for manual assignments
- Drag-and-drop between team members

## 📞 Support

For questions or issues with this release:
- Review updated documentation
- Check CHANGELOG.md for detailed changes
- Contact development team for migration assistance

## 🙏 Acknowledgments

This release includes significant enhancements to improve workflow efficiency and administrative control over the CallerID review process.

---

**Previous Version**: 0.1.0 (Initial PoC)  
**Current Version**: 0.2.0 (Enhanced PoC)  
**Next Planned**: 0.3.0 (Additional PoC features) or 1.0.0 (Production release)
