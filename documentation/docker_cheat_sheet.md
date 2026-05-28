# Docker useful commands 

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