# Low-miss discovery update

The shortlist is no longer the boundary of discovery. Every captured notice is published to a separate searchable index, including unknown and clearly excluded scope. Broad chemistry, cooling, steam-cycle, dosing, instrumentation and display language can generate a review candidate without passing strict portfolio rules. Attachment filenames are searchable; punctuation variants are normalised. Clear unrelated scopes remain outside review/shortlist but are still searchable.

Current public capture: 2,387 notices, 2 matched candidates and 88 review items. Counts include notices from multiple sources; they are not a promise of unique projects or complete market coverage. Water Boards remains partial (Umgeni fetch failed this run; Magalies returned 404).

Source failure does not silently erase prior captured records from the affected group: retained records are flagged stale and require currency checks. Primary-feed failure retains the previous snapshot. Shared reference numbers from different buyers remain distinct. Missing/unverified deadlines stay in discovery/review rather than being silently discarded or presented as confirmed open matches.

Verification: 299 Python tests passed in the full run; 2 further refresh integration checks passed for shared refs/undated records and primary-feed failure. Dashboard: 38 tests, lint, typecheck and browser smoke passed. Ruff and diff checks passed. Curated positive retrieval examples include MWP3022CX interactive LED touch panels, OLT2105326 dosing/monitoring of Mexel 432, ODACON boiler corrosion inhibitor, surface-active chemistry, condensate preservation and instrumentation. All curated positive examples were retained as strong or possible candidates. This is regression evidence, not a measured real-world recall rate; independent-feed benchmarking remains necessary.

Browser verification: loading the index and searching monitor returned 45 captured notices beyond the shortlist without document overflow. No database writes, notifications or installed schedule changes were performed. No separate monitor readvertisement was confirmed.
