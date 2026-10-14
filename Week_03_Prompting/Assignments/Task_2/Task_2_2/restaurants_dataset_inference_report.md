# Restaurant query inference report

## Timing and usage

- **Inference time:** 901,507 ms, measured from the initial inspection of the Task_2_2 inputs at 2026-10-14 13:44:48.857 (+02:00) through generation of `restaurants_dataset_predictions.csv`.
- **Tokens spent:** unavailable.
- **Credits spent:** unavailable.

## Files and verified data structure

The Task_2_2 folder contains `ICIO.md` (the task specification), `restaurants_dataset.csv` (155 question/answer pairs), `restaurants-schema.csv` (schema), and `restaurants-db.txt` (the text-format data dump). The generated `restaurants_dataset_predictions.csv` contains the 155 questions in their original order and a SQL query for each.

The schema declares:

- `RESTAURANT`: `ID` primary key; restaurant `NAME`, `FOOD_TYPE`, `CITY_NAME`, and `RATING`. `CITY_NAME` references `GEOGRAPHIC.CITY_NAME`.
- `LOCATION`: `RESTAURANT_ID` primary/foreign key to `RESTAURANT.ID`; `HOUSE_NUMBER`, `STREET_NAME`, and `CITY_NAME`. Its city references `GEOGRAPHIC.CITY_NAME`.
- `GEOGRAPHIC`: `CITY_NAME` primary/foreign key; `COUNTY` and `REGION`.

The verified joins are `RESTAURANT.ID = LOCATION.RESTAURANT_ID` for addresses and `RESTAURANT.CITY_NAME = GEOGRAPHIC.CITY_NAME` for geographic region filters. Inspection of the text dump found 9,589 restaurant records, 9,274 location records, and 167 geographic records. No SQLite engine was run.

## Query construction

Queries use the requested result shape—house number and restaurant name—and constrain only columns and relationships present in the schema. City and address questions filter by the location city and, where given, the street; food-category questions use the exact `FOOD_TYPE`; rating thresholds use strict `RATING > threshold`; region questions join `GEOGRAPHIC` and filter `REGION`. “Best” questions sort by rating descending and return the top row. Irrelevant menu asides in the natural-language questions are not treated as database filters.

The supplied answers support these interpretations: the Portola Valley Californian question identifies `portola park` at house number 3; the Calistoga eclectic question identifies `catahoula restaurant and saloon` at 1457; and the Timber Creek Drive question identifies `lee & ginas cafe` at 1503 with a rating above 1.7.

## Ambiguity and answer consistency

Question 66, “What is the lifes greates illusion?”, gives no restaurant, location, food type, or other usable database constraint. Its supplied answer nevertheless contains 2,696 restaurant/address pairs. There is no reliable way to infer the intended query or reproduce that answer from the wording without inventing criteria. Its prediction is therefore an explicit empty-result query, and this question remains unresolved against its supplied answer.

Question 88 asks for restaurants in “the unknown.” The dump contains `unknown` as an actual `GEOGRAPHIC.REGION` value, so the prediction treats it as a region, not as a city placeholder.
