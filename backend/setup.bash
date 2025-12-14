# python -m venv venv

source venv/Scripts/activate

pip install -r requirements.txt

# Option to run the health check setup
if [ "$1" == "--setup-health-check" ]; then
    echo "Setting up health check environment..."
    bash setup_health_check.bash --setup-only
    exit 0
fi

# Option to run health checks
if [ "$1" == "--run-health-check" ]; then
    echo "Running health checks..."
    bash setup_health_check.bash $2 $3 $4 $5 $6
    exit $?
fi

uvicorn main:app --reload --port 8000

# Initialize Supabase project
npx supabase init --force
 
# Login to Supabase
npx supabase login

# Link your project
npx supabase link --project-ref merenxqjwiujvtkgquum

# Create a new migration
npx supabase migration new schema_sql
 
# Run migrations
npx supabase db push

# Fetch latest migrations
npx supabase migration fetch