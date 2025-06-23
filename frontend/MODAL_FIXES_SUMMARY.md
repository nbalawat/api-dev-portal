# Modal Title and Button Visibility Fixes

## Issues Fixed:
1. **Modal title not visible** - The template selector modal title was not visible, especially in dark mode
2. **Cancel button not visible** - The Cancel button had transparent background with outline variant
3. **Inconsistent modal styling** - The modal was using a basic HTML implementation instead of the proper Dialog component

## Changes Made:

### 1. Dashboard Page (`src/app/dashboard/page.tsx`)
- Added Dialog component imports from shadcn/ui
- Replaced custom modal implementation with proper Dialog component
- Changed from:
  ```jsx
  <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
    <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-y-auto">
  ```
  To:
  ```jsx
  <Dialog open={showTemplateSelector} onOpenChange={setShowTemplateSelector}>
    <DialogContent className="max-w-6xl w-full max-h-[90vh] overflow-y-auto">
  ```

### 2. Template Selector Component (`src/components/key-management/template-selector.tsx`)
- Fixed all heading colors by adding dark mode classes
- Fixed Cancel button styling with explicit background and border colors
- Updated multiple text elements:
  - Main title: `text-gray-900 dark:text-gray-100`
  - Descriptions: `text-gray-600 dark:text-gray-400`
  - Cancel buttons: Added explicit styling with background and hover states
  - Primary action button: Uses blue background for better visibility

### 3. TypeScript Fixes
- Fixed TypeScript errors in `analytics-chart.tsx` and `analytics-filters.tsx`
- Added proper type annotations for map functions

## Result:
- Modal title is now clearly visible in both light and dark modes
- Cancel button has proper background and border styling
- All buttons in modal footers have consistent styling
- Modal properly respects the application's theme
- Better accessibility with proper ARIA attributes
- Escape key and clicking outside will close the modal
- Proper focus management

## Testing:
1. Navigate to http://localhost:3000/dashboard
2. Click "Create from Template" button
3. Verify:
   - Modal title "Create API Key from Template" is clearly visible
   - Cancel button at bottom left has visible background and border
   - All text is readable with proper contrast
   - Modal background respects the current theme (light/dark)