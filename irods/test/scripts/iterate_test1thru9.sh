cd "$(dirname "$0")"
for s in $*;do
  ../harness/docker_container_driver.sh "$s" || exit 123
done
