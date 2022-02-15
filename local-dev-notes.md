To get a shell to run integration tests:

```
docker run -it \
-v $(pwd)/samples:/fmc-ansible/playbooks \
-v $(pwd)/ansible.cfg:/fmc-ansible/ansible.cfg \
-v $(pwd)/requirements.txt:/fmc-ansible/requirements.txt \
-v $(pwd)/inventory/sample_hosts:/etc/ansible/hosts \
--entrypoint /bin/bash \
fmc-ansible:integration
```

To build a docker file for local module development:

```
docker build -t fmc-ansible:dev -f Dockerfile_dev .
```

To get a shell in container to develop locally / run playbooks

```
docker run -it -p 8080:8080 \
-v $(pwd)/samples:/fmc-ansible/playbooks \
-v $(pwd)/ansible.cfg:/fmc-ansible/ansible.cfg \
-v $(pwd)/requirements.txt:/fmc-ansible/requirements.txt \
-v $(pwd)/inventory/sample_hosts:/etc/ansible/hosts \
--entrypoint /bin/bash \
fmc-ansible:dev
```

Run a playbook (and keep  local modules which isn't working for me - should be at /root/.ansible/tmp but they are deleted after playbook run):
```
cd /fmc-ansible/

ANSIBLE_KEEP_REMOTE_FILES=1 ansible-playbook -i /etc/ansible/hosts playbooks/fmc_configuration/latest.yml -vvvv
```

Add debugger to module code (requires rebuilding container):
```
import epdb;
epdb.serve(port=8080)
```

Set debugger breakpoints:
```
# epdb.set_trace()
```

To connect to debugger in container from local machine (can also use other epdb utilities):
```
python -c "import epdb; epdb.connect(host='localhost', port=8080)"
```
