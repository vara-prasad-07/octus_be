"""
Test script for date utility functions
"""
from date_utils import parse_date, excel_serial_to_date, format_date_for_display, days_until_date
from datetime import datetime


def test_date_parsing():
    """Test various date format parsing"""
    print("Testing Date Parsing Functions")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        # Excel serial dates
        (45372.22928240741, "Excel serial date"),
        (45371.22928240741, "Excel serial date 2"),
        (45373.22928240741, "Excel serial date 3"),
        
        # ISO format dates
        ("2024-03-15", "ISO date"),
        ("2024-03-15T10:30:00", "ISO datetime"),
        ("2024-03-15T10:30:00Z", "ISO datetime with Z"),
        
        # Other formats
        ("2024/03/15", "Slash format"),
        ("03/15/2024", "US format"),
        ("15/03/2024", "EU format"),
        
        # Edge cases
        (None, "None value"),
        ("", "Empty string"),
        ("invalid", "Invalid string"),
    ]
    
    for date_value, description in test_cases:
        result = parse_date(date_value)
        display = format_date_for_display(date_value)
        print(f"\n{description}:")
        print(f"  Input:   {date_value}")
        print(f"  Parsed:  {result}")
        print(f"  Display: {display}")
        
        if result:
            days = days_until_date(date_value)
            print(f"  Days until: {days}")
    
    print("\n" + "=" * 50)
    print("Testing Excel Serial Date Conversion")
    print("=" * 50)
    
    # Test specific Excel serial dates
    excel_dates = [45372, 45371, 45373, 45381, 45363, 45369, 45377, 45375, 45374, 45383]
    
    for serial in excel_dates:
        dt = excel_serial_to_date(serial)
        if dt:
            print(f"Excel {serial} -> {dt.strftime('%Y-%m-%d')} ({dt.strftime('%b %d, %Y')})")
    
    print("\n" + "=" * 50)
    print("All tests completed!")


if __name__ == "__main__":
    test_date_parsing()
