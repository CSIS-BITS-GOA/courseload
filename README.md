# Faculty Workload Estimator

A Flask web application to calculate teaching workload for faculty members.

## Features

- Course workload calculation (lectures, tutorials, practicals)
- Stores data in SQLite database (`workload_data.db`)
- Admin dashboard to view all submissions
- Export results as PDF and CSV for the user to download


## Access

- Faculty form: `http://localhost:5001`
- Admin view: `http://localhost:5001/admin/data`

## Files

```
academic_workload.py                   # Main application
courses.csv                            # Course database
templates/
├── form.html                          # Input form
├── result.html                        # Results page
└── admin_data.html                    # Admin dashboard
static/
├── Logo_horizontal_ShortFormat.png    # BITS logo
```
