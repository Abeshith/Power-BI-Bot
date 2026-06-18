# Testing Dynamic Schema Discovery with Sales Dataset

## New Dataset: sales_data.csv
**Location**: `d:\Power BI Bot\sample_data\sales_data.csv`

**Columns**:
- `date`: Order date (Jan-Mar 2026)
- `region`: North, South, East, West (4 values)
- `product`: Laptop, Monitor, Chair, Desk, Mouse, Keyboard, Lamp, Notebook, Pen (9 values)
- `category`: Electronics, Furniture, Stationery (3 values)
- `quantity`: Order quantity (numeric)
- `revenue`: Sale amount (numeric)
- `profit`: Profit amount (numeric)
- `sales_rep`: Alice, Bob, Charlie, Diana (4 values)

## How to Test Dynamic Schema Discovery

### Step 1: Create New Power BI Dashboard
1. Open Power BI Desktop
2. Create new blank report
3. Import `sales_data.csv` as data source
4. Name the table: `sales`

### Step 2: Add 2 Simple Charts

**Chart 1: Revenue by Region**
- X-axis: `region`
- Y-axis: Sum of `revenue`
- Type: Column chart
- Purpose: Test single categorical filter

**Chart 2: Quantity by Category**
- X-axis: `category`
- Y-axis: Sum of `quantity`
- Type: Column chart
- Purpose: Test different column filtering

### Step 3: Add Power BI Bot Visual
1. Import the latest pbiviz file
2. Add it to the dashboard
3. NO NEED to configure data fields (dynamic schema will do it)

### Step 4: Test Queries

**Query 1 (Single Filter - Should Work)**
```
"Electronics products"
```
Expected: Revenue chart shows only Electronics category, Quantity chart filters to Electronics

**Query 2 (Single Filter)**
```
"North region sales"
```
Expected: Both charts filter to show only North region data

**Query 3 (Single Filter)**
```
"Show me West"
```
Expected: Charts show only West region

**Query 4 (Multi-Filter - Tests Dynamic Extraction)**
```
"Electronics products from North"
```
Expected: Should filter to category=Electronics AND region=North
- Revenue chart: Only North electronics
- Quantity chart: Only North electronics

**Query 5 (Another Multi-Filter Test)**
```
"Furniture in South"
```
Expected: Filter to category=Furniture AND region=South

## What to Look For

✅ **Dynamic Schema Works If:**
1. Bot message shows: "Applied 1 filter(s): ..." for single queries
2. Bot message shows: "Applied 2 filter(s): ..." for multi-queries
3. Charts update immediately to show filtered data
4. Single-column filters work correctly

⚠️ **If Multi-Filters Fail:**
- Single filters will still work (we know this works)
- Multi-filter queries will show same result as single filter
- This helps us diagnose if it's Power BI behavior vs. hospital data issue

## Why This Dataset is Better
1. **Clearer data**: Sales/regional data is more intuitive
2. **Clean combinations**: All combinations of category+region exist in data
3. **Generic columns**: Not hospital-specific, proves dynamic approach works universally
4. **Smaller dataset**: Easier to verify results manually
