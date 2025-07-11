# Scripts Directory

This directory was previously used for database setup and utility scripts, but those files have been removed as they are not needed for the core application functionality.

## 📄 Current Status

**No scripts currently present** - All database modification scripts have been removed since:
- The application uses SQLAlchemy ORM for database operations
- Database tables are created automatically by the application
- Migration and setup scripts are not needed for core functionality

## 🔗 Related

- **Main Tests**: [`../tests/`](../tests/) - Comprehensive pytest test suite (43 tests)
- **Test Runner**: [`../run_tests.py`](../run_tests.py) - Main test runner interface
- **Documentation**: [`../docs/TESTING_GUIDE.md`](../docs/TESTING_GUIDE.md) - Testing guide

---

**Note**: All database operations are now handled through the main application using SQLAlchemy models and ORM functionality. 