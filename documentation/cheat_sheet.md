# Useful commands

## Docker

Launching the VM on the server require this command : 

```bash
sudo docker compose -f docker-compose.vm.yml up -d --build
```

Stopping the VM : 
```bash
sudo docker compose -f docker-compose.vm.yml down
```

To consult the logs live : 
```bash
sudo docker compose -f docker-compose.vm.yml logs -f
```
## Chacha access

To access chacha directly, connection should be made from the VM docker: 
```bash
# access to the VM
ssh jeremy.duc@153.109.8.48

cd apps/a-eye_web/

# access to chacha
sudo docker exec -it aeyeweb ssh chacha

# To observe running/pending jobs
squeue -u jaime.barrancohernandez
```