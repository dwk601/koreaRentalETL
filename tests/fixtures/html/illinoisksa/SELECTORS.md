# illinoisksa.org/housing — Confirmed Selectors

Probed on 2026-05-28 against live site.

## Fetcher Decision
**Fetcher** (plain HTTP GET). curl returns HTTP 200 with 333KB body. Zero Cloudflare markers.

## List Page Selectors

| Element | Selector | Notes |
|---------|----------|-------|
| Table root | `table > tbody` | Plain table, no KBoard list classes on the table itself |
| Row | `tbody > tr` | All rows are direct children of tbody |
| Notice row | `tr.kboard-list-notice` | 3 pinned notices (공지사항); must be filtered out |
| Data row | `tr` without `.kboard-list-notice` | 10 per page |
| UID cell | `td.kboard-list-uid` | Row number (not the source listing ID) |
| Title cell | `td.kboard-list-title` | Contains the anchor |
| Title anchor | `td.kboard-list-title > a[href*="mod=document"][href*="uid="]` | href like `/housing/?mod=document&uid=13972` |
| Date cell | `td.kboard-list-date` | Format: `YYYY.MM.DD` (e.g. `2026.05.26`) |
| Author cell | `td.kboard-list-user` | |
| View cell | `td.kboard-list-view` | |

### Source listing ID
Extracted from anchor href: `re.search(r'uid=(\d+)', href)`.

### Pagination
Pattern: `?pageid=N&mod=list` (pageid=1..79). Page links found via `a[href*="pageid="]`.

## Detail Page Selectors

| Element | Selector | Notes |
|---------|----------|-------|
| Title | `.kboard-title h1` | Clean title, no suffix to strip |
| Date | `.detail-attr.detail-date` | Contains "작성일" prefix + datetime like `2026-05-26 16:46` |
| Author | `.detail-attr.detail-writer` | Contains "작성자" prefix |
| Body | `.kboard-content .content-view` | Main content area |

### Detail URL pattern
`https://illinoisksa.org/housing/?mod=document&uid=<N>`

### Notes
- Detail pages have structured meta in `.kboard-detail` with `.detail-attr` children
- No separate meta table for 위치/월세/보증금 — these are embedded in the body text if present
- Body text is free-form (no structured label:value pairs like gtksa)
