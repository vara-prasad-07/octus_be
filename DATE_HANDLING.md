# Date Handling in Octus Backend

## Overview

The Octus backend now supports multiple date formats, including Excel serial dates, which are commonly encountered when importing data from spreadsheets.

## Supported Date Formats

### 1. Excel Serial Dates
- **Format**: Numeric values like `45372.22928240741`
- **Description**: Days since 1900-01-01 (Excel's date system)
- **Example**: `45372` = March 21, 2024

### 2. ISO Format Dates
- **Format**: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`
- **Examples**: 
  - `2024-03-15`
  - `2024-03-15T10:30:00`
  - `2024-03-15T10:30:00Z`

### 3. Common Date Formats
- **Slash format**: `2024/03/15`
- **US format**: `03/15/2024`
- **EU format**: `15/03/2024`

## Date Utility Functions

### `parse_date(date_value)`
Converts any supported date format to ISO format string (YYYY-MM-DD).

```python
from date_utils import parse_date

# Excel serial date
parse_date(45372.22928240741)  # Returns: "2024-03-21"

# ISO format
parse_date("2024-03-15")  # Returns: "2024-03-15"

# Other formats
parse_date("03/15/2024")  # Returns: "2024-03-15"
```

### `excel_serial_to_date(serial)`
Converts Excel serial date to Python datetime object.

```python
from date_utils import excel_serial_to_date

dt = excel_serial_to_date(45372)
# Returns: datetime(2024, 3, 21, 0, 0)
```

### `format_date_for_display(date_value)`
Formats any date for human-readable display.

```python
from date_utils import format_date_for_display

format_date_for_display(45372)  # Returns: "Mar 21, 2024"
format_date_for_display("2024-03-15")  # Returns: "Mar 15, 2024"
```

### `days_until_date(date_value, from_date=None)`
Calculates days until a given date.

```python
from date_utils import days_until_date

days = days_until_date("2024-12-31")
# Returns: number of days from now until Dec 31, 2024
```

## Integration with Models

The `TaskInput` model automatically validates and normalizes dates:

```python
from models import TaskInput

# Excel serial date is automatically converted
task = TaskInput(
    id="1",
    name="Task",
    dueDate=45372.22928240741  # Automatically converted to "2024-03-21"
)

# ISO format is validated
task = TaskInput(
    id="2",
    name="Task",
    dueDate="2024-03-15"  # Validated and kept as-is
)
```

## Risk Engine Integration

The `RiskEngine` now handles all date formats when calculating deadline risk:

```python
from risk_engine import RiskEngine

engine = RiskEngine()

# Works with Excel serial dates
risk = engine.calculate_deadline_risk(45372.22928240741)

# Works with ISO dates
risk = engine.calculate_deadline_risk("2024-03-15")
```

## Testing

Run the test suite to verify date parsing:

```bash
cd octus_be
python test_date_utils.py
```

## Error Handling

- Invalid dates return `None` instead of raising exceptions
- The system logs warnings for unparseable dates
- Default risk scores are applied when dates cannot be parsed

## Frontend Integration

The frontend uses matching date utilities (`src/utils/dateUtils.js`) to ensure consistency:

- Excel serial dates from imported spreadsheets are converted
- Dates are displayed in human-readable format
- Date inputs use ISO format (YYYY-MM-DD)
- Backend receives properly formatted dates

## Migration Notes

If you have existing data with Excel serial dates:

1. The system will automatically convert them on the next API call
2. No manual migration is required
3. All date formats are normalized to ISO format (YYYY-MM-DD) in the database
