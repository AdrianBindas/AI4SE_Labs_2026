# Restaurants dataset SQL predictions report

- Queries generated: 155
- Inference time: 478834 ms (from first relevant-file inspection at 2026-10-14T14:30:28.179+02:00 through saving `restaurants_dataset_predictions.csv` at 2026-10-14T14:38:27.012+02:00)
- Tokens spent during this interval: unavailable from session telemetry
- Credits spent during this interval: unavailable from session telemetry

## Assumptions

- The answer pair's first value represents `LOCATION.HOUSE_NUMBER`, not `RESTAURANT.ID`; each query therefore selects `L.HOUSE_NUMBER` and `R.NAME` and joins `LOCATION` through `LOCATION.RESTAURANT_ID = RESTAURANT.ID`.
- City and cuisine filters use the matching `RESTAURANT` fields; street/address questions use `LOCATION.STREET_NAME` and `LOCATION.CITY_NAME`. Geographic-area questions use `GEOGRAPHIC.REGION` joined by city.
- Rating phrases such as “above 2” are strict `>` comparisons. “Best” means highest rating and is limited to one row; other requests return all matching rows, ordered by rating descending.
- Row 66 (“What is the lifes greates illusion?”) contains no restaurant-related condition and cannot be answered reliably from this schema. Its query returns all restaurants with locations, ranked by rating, as a broad fallback rather than inventing unsupported filters.
- Queries were constructed from the supplied schema, text dump, questions, and answer examples. The SQLite engine was not run; query execution and empirical correctness are not claimed.
