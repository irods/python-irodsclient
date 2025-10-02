cd "$(dirname "$0")"
fmt=$(cat <<-EOF
        ********************
        ***      %02d      ***
        ********************
	EOF
)
for x in {0..9}; do
  printf "$fmt\n" $x
  for s in test00[1-9]*; do 
    DOCKER=podman ../harness/docker_container_driver.sh "$s"
  done
done

