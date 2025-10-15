# Database Setup Guide

This guide explains how to set up PostgreSQL database connection for the backend.

## Prerequisites

1. **PostgreSQL Installation**
   - Install PostgreSQL 12 or higher
   - On Windows: Download from [postgresql.org](https://www.postgresql.org/download/windows/)
   - On macOS: `brew install postgresql`
   - On Linux: `sudo apt-get install postgresql postgresql-contrib`

2. **Python Dependencies**
   ```bash
   cd Backend
   pip install -r requirements-db.txt
   ```

## Configuration

1. **Create Environment File**
   
   Create a `.env` file in the `Backend` directory:
   ```bash
   cp env.example.txt .env
   ```

2. **Update Database Credentials**
   
   Edit the `.env` file with your PostgreSQL credentials:
   ```env
   DATABASE_URL=postgresql://your_username:your_password@localhost:5432/electron_app_db
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=electron_app_db
   DB_USER=your_username
   DB_PASSWORD=your_password
   ```

3. **Create Database**
   
   Connect to PostgreSQL and create the database:
   ```bash
   # On Windows (PowerShell)
   psql -U postgres
   
   # In psql prompt
   CREATE DATABASE electron_app_db;
   \q
   ```

4. **Initialize Database Tables**
   
   Run the initialization script:
   ```bash
   cd Backend
   python init_db.py
   ```

## Database Models

The application includes three main models:

### 1. Document
Stores parsed documents and their metadata.

**Fields:**
- `id`: Primary key
- `filename`: Original filename
- `file_type`: File extension (pdf, jpg, png)
- `task_type`: Processing task (parse, text, table, etc.)
- `content`: Extracted content
- `metadata`: JSON metadata
- `output_path`: Path to output files
- `status`: Processing status
- `created_at`, `updated_at`: Timestamps

### 2. ProcessingJob
Tracks asynchronous processing jobs.

**Fields:**
- `id`: Primary key
- `job_id`: UUID for the job
- `job_type`: Type of processing
- `input_file`: Input file path
- `output_files`: JSON array of output paths
- `status`: Job status (pending, processing, completed, failed)
- `progress`: Progress percentage (0-100)
- `result_data`: JSON result data
- `started_at`, `completed_at`: Timestamps

### 3. User
User management (optional).

**Fields:**
- `id`: Primary key
- `username`: Unique username
- `email`: Unique email
- `full_name`: Full name
- `hashed_password`: Encrypted password
- `is_active`: Account status
- `is_superuser`: Admin flag

## API Endpoints

Once the backend is running with database support, the following endpoints are available:

### Documents
- `GET /api/documents` - List all documents
- `GET /api/documents/{id}` - Get specific document
- `POST /api/documents` - Create document record
- `PATCH /api/documents/{id}` - Update document
- `DELETE /api/documents/{id}` - Delete document

### Processing Jobs
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/{job_id}` - Get specific job
- `POST /api/jobs` - Create job
- `PATCH /api/jobs/{job_id}` - Update job status
- `DELETE /api/jobs/{job_id}` - Delete job

### Health Check
- `GET /api/health` - Check database connection

## Running the Backend

```bash
cd Backend
python api/main.py
```

The backend will:
1. Load environment variables from `.env`
2. Connect to PostgreSQL
3. Initialize database tables (if they don't exist)
4. Start the FastAPI server on port 7861

## Frontend Configuration

1. **Create Environment File**
   
   In the `Frontend` directory, create `.env`:
   ```bash
   VITE_API_URL=http://localhost:7861
   ```

2. **Use API Client**
   
   Import and use the API client in your React components:
   ```typescript
   import { apiClient } from '@/lib/api';
   
   // Get documents
   const documents = await apiClient.getDocuments();
   
   // Parse a file
   const result = await apiClient.parseDocument(file);
   
   // Create a job
   const job = await apiClient.createJob({
     job_type: 'parse',
     input_file: 'document.pdf'
   });
   ```

## Troubleshooting

### Connection Issues

1. **Check PostgreSQL is running:**
   ```bash
   # Windows
   Get-Service postgresql*
   
   # Linux/macOS
   sudo systemctl status postgresql
   ```

2. **Verify credentials:**
   - Ensure username and password are correct
   - Check that the database exists
   - Verify the port (default: 5432)

3. **Check firewall:**
   - PostgreSQL port 5432 should be accessible
   - On Windows, check Windows Firewall settings

### Database Errors

1. **"Database does not exist"**
   - Create the database: `CREATE DATABASE electron_app_db;`

2. **"Password authentication failed"**
   - Update PostgreSQL `pg_hba.conf` to allow password authentication
   - Restart PostgreSQL after changes

3. **"Too many connections"**
   - Adjust `pool_size` in `Backend/database.py`
   - Increase `max_connections` in PostgreSQL config

## Optional: pgAdmin

For easier database management, install pgAdmin:
- Download from [pgadmin.org](https://www.pgadmin.org/download/)
- Connect using your database credentials
- View tables, run queries, and manage data visually

## Security Notes

1. **Never commit `.env` file** - It contains sensitive credentials
2. **Use strong passwords** for production
3. **Enable SSL** for production databases
4. **Implement authentication** before deploying
5. **Regular backups** of the database

## Next Steps

- Implement user authentication
- Add more complex queries
- Set up database migrations with Alembic
- Add database indexing for better performance
- Implement caching layer

