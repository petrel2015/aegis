<!-- Fictional user-documentation example, not a verified product feature. -->
## Export filtered tasks as CSV

### Purpose and scope
Download the currently visible task rows for offline analysis. Hidden rows are excluded.

### Usage
Apply a task filter, then choose Export CSV in the toolbar. The browser downloads tasks.csv.
No server export or scheduled delivery is provided.

### Example
Filter to one task named `Plan, review`. The CSV cell is quoted as `"Plan, review"` so its
comma remains part of the name rather than creating another column.

### Errors and limits
If the browser blocks downloads, allow downloads for the site and retry the action.
Supported browsers follow the project's documented compatibility matrix.

### Change reference
Issue #42; approved design record D1; PR #57. Replace these illustrative references with
actual durable links when publishing this section.
