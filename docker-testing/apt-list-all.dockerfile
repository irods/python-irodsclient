ARG linux_vsn="ubuntu:18.04"
FROM ${linux_vsn}
RUN       apt update
RUN       apt install -y lsb-release apt-transport-https
RUN apt install -y wget
RUN apt install -y gnupg2
RUN       wget -qO - https://packages.irods.org/irods-signing-key.asc | apt-key add -
RUN       echo "deb [arch=amd64] https://packages.irods.org/apt/ $(lsb_release -sc) main" |\
              tee "/etc/apt/sources.list.d/renci-irods.list"
RUN       apt update

ENTRYPOINT ["apt", "list", "-a"]

