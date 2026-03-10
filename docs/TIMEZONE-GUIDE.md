# Timezone Implementation Guide

## Overview
The application now displays all datetimes in the user's local timezone while continuing to store everything in UTC in the database.

## How It Works

### Backend (Unchanged - Already Using UTC)
- All datetime values are stored in UTC in the database
- Python datetime objects use `timezone.utc`
- ISO 8601 format timestamps sent to frontend

### Frontend (New Implementation)
- JavaScript utility automatically converts UTC to local timezone
- Uses browser's `Intl` API for locale-aware formatting
- No manual timezone configuration needed

## User Experience Examples

### User in CDT (Central Daylight Time - UTC-05:00)
```
Backend stores: 2026-03-09T19:30:00+00:00 (UTC)
User sees:      2:30 PM (CDT)
```

### User in IST (India Standard Time - UTC+05:30)
```
Backend stores: 2026-03-09T19:30:00+00:00 (UTC)
User sees:      1:00 AM (IST)
```

### User in UTC
```
Backend stores: 2026-03-09T19:30:00+00:00 (UTC)
User sees:      7:30 PM (UTC)
```

## Implementation Details

### Files Modified

1. **templates/timezone_utils.html** (NEW)
   - JavaScript utility library for timezone conversion
   - Provides `TimezoneUtils` global object
   - Auto-converts timestamps on page load

2. **templates/base.html**
   - Includes `timezone_utils.html` globally
   - Available on all pages

3. **All Dashboard Templates**
   - Added `data-utc` attributes with ISO timestamps
   - Added `data-format` attributes (time|datetime|date|relative)
   - Server-side formatting kept as fallback for non-JS browsers

### Timezone Utility Functions

```javascript
// Convert UTC to local time
TimezoneUtils.formatTime('2026-03-09T19:30:00+00:00')
// Returns: "2:30 PM" (in user's format)

// Full datetime
TimezoneUtils.formatDateTime('2026-03-09T19:30:00+00:00')
// Returns: "Mar 9, 2026, 2:30 PM"

// Relative time
TimezoneUtils.formatRelative('2026-03-09T19:30:00+00:00')
// Returns: "2 hours ago"

// Get user's timezone
TimezoneUtils.getUserTimezone()
// Returns: "CDT" or "IST" or "UTC"

// Get UTC offset
TimezoneUtils.getUtcOffset()
// Returns: "-05:00" or "+05:30"
```

### HTML Usage Pattern

**Before (Server-side only)**:
```html
<td>{{ timestamp.strftime('%H:%M, %d %b') }}</td>
```

**After (Client-side conversion with fallback)**:
```html
<td data-utc="{{ timestamp.isoformat() }}" data-format="datetime">
  {{ timestamp.strftime('%H:%M, %d %b') }}
</td>
```

The JavaScript automatically updates the content on page load.

## Features

### Automatic Conversion
All timestamps with `data-utc` attribute are automatically converted when page loads.

### Format Options
- `data-format="time"` → "2:30 PM"
- `data-format="datetime"` → "Mar 9, 2026, 2:30 PM"
- `data-format="date"` → "March 9, 2026"
- `data-format="short-date"` → "3/9/2026"
- `data-format="relative"` → "2 hours ago"

### Hover Tooltips
Elements display full datetime in tooltip for additional context.

### Timezone Display
Reports page shows: "Your timezone: CDT (UTC-05:00)"

## Browser Compatibility

### Required Features
- `Intl.DateTimeFormat` (ES6)
- `Date.prototype.toLocaleString`
- `dataset` attribute support

### Supported Browsers
- ✅ Chrome 24+
- ✅ Firefox 29+
- ✅ Safari 10+
- ✅ Edge (all versions)
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

### Fallback
Server-rendered timestamps still display for non-JavaScript users (shows UTC times).

## Testing

### Test Different Timezones
1. **Change System Timezone**:
   - Windows: Settings → Time & Language → Date & Time
   - Mac: System Preferences → Date & Time → Time Zone
   - Linux: `timedatectl set-timezone America/Chicago`

2. **Browser DevTools**:
   - Chrome: DevTools → More tools → Sensors → Location
   - Can emulate different timezones

3. **Check Console**:
   - Open browser console (F12)
   - Look for: "User Timezone: CDT UTC Offset: -05:00"

### Verification Steps
1. Login to any dashboard
2. Check browser console for timezone log
3. Verify times match your system clock
4. Hover over timestamps to see full datetime tooltip
5. Check Reports page footer for timezone display

## Database Verification

All datetimes in database should remain in UTC:

```sql
-- Check attendance logs
SELECT clock_in_time FROM attendance_logs;
-- Should show: 2026-03-09 19:30:00 (UTC)

-- Check assignments
SELECT assigned_at FROM assignments;
-- Should show: 2026-03-09 14:15:00 (UTC)
```

## Debugging

### Console Logs
```javascript
// Check if timezone utils loaded
console.log(window.TimezoneUtils);

// Get current timezone info
console.log(TimezoneUtils.getUserTimezone());
console.log(TimezoneUtils.getUtcOffset());

// Test conversion
console.log(TimezoneUtils.formatDateTime('2026-03-09T19:30:00+00:00'));
```

### Common Issues

**Times not converting?**
- Check console for JavaScript errors
- Verify `data-utc` attribute has valid ISO timestamp
- Ensure `timezone_utils.html` is included

**Wrong timezone displayed?**
- Check system timezone settings
- Verify browser locale settings
- Clear browser cache

**Timers not updating?**
- Check for JavaScript errors in console
- Verify `updateTimers()` function is running
- Check data attributes on timer elements

## Performance

- **Zero backend overhead**: All conversion happens client-side
- **Minimal JavaScript**: ~200 lines of utility code
- **No external libraries**: Uses native browser APIs
- **Cached DOM queries**: Efficient updates every second for timers

## Security

- No timezone data sent to server
- No user tracking based on timezone
- All conversion happens locally in browser
- UTC storage prevents timezone-related vulnerabilities
