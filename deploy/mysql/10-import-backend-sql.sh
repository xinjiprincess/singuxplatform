set -e

init_sql=/backend-sql/init.sql

if [ ! -f "$init_sql" ]; then
  echo "Backend SQL file $init_sql does not exist, skipping import."
  return 0 2>/dev/null || exit 0
fi

echo "Importing $init_sql into ${MYSQL_DATABASE}"
mysql \
  --protocol=socket \
  -uroot \
  -p"${MYSQL_ROOT_PASSWORD}" \
  "${MYSQL_DATABASE}" < "$init_sql"
