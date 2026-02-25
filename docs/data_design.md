## InspectionRecords
 - inspection_date
 - qty_defects
## Lot
 - lot_id
## Defect
 - defect_code
## Relationships
 - One lot can have many inspection records
 - One defect can exist in many inspection records

## ERD
```mermaid
erDiagram
    LOT ||--o{ INSPECTION_RECORD : has
    DEFECT ||--o{ INSPECTION_RECORD : appears_in

    LOT {
        lot_id string
    }

    DEFECT {
        defect_code string
    }

    INSPECTION_RECORD {
        inspection_date string
        qty_defects int
    }
```
