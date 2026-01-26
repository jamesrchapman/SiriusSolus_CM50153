# Next

- Update Service

```bash
sudo cp bennycareserver.service /etc/systemd/system
```

- Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bennycareserver.service
```

- logs and status

```bash
systemctl status bennycareserver.service
journalctl -u bennycareserver.service -f
```

1) Edit the unit file
sudo nano /etc/systemd/system/bennycareserver.service

2) Tell systemd to re-read unit files
sudo systemctl daemon-reload

3) Restart the service
sudo systemctl restart bennycareserver.service

4) Check status + logs
systemctl status bennycareserver.service --no-pager
journalctl -u bennycareserver.service -n 60 --no-pager

## Ideas

1. Honey Feeder
2. Designing Honey Feeder
3. Building Honey Feeder
4. Testing Honey Feeder
5. Failure Points Honey Feeder
6. Redundancies Honey FeederKibble Feeder
7. Designing Kibble Feeder
8. Building Kibble Feeder
9. Testing Kibble Feeder
10. Failure Points Kibble Feeder
11. Redundancies Kibble FeederCamera Mount
12. Designing Camera Mount
13. Building Camera Mount
14. Testing Camera Mount
15. Failure Points Camera Mount
16. Redundancies Camera MountFeeding Chime
17. Designing Feeding Chime
18. Building Feeding Chime
19. Testing Feeding Chime
20. Failure Points Feeding Chime
21. Redundancies Feeding ChimeLibre Graph
22. Designing Libre Graph
23. Building Libre Graph
24. Testing Libre Graph
25. Failure Points Libre Graph
26. Redundancies Libre GraphRedundant Data Access
27. Designing Redundant Data Access
28. Building Redundant Data Access
29. Testing Redundant Data Access
30. Failure Points Redundant Data Access
31. Redundancies Redundant Data AccessRedundant Control Access
32. Designing Redundant Control Access
33. Building Redundant Control Access
34. Testing Redundant Control Access
35. Failure Points Redundant Control Access
36. Redundancies Redundant Control AccessRedundant Monitoring Access
37. Designing Redundant Monitoring Access
38. Building Redundant Monitoring Access
39. Testing Redundant Monitoring Access
40. Failure Points Redundant Monitoring Acces
41. Redundancies Redundant Monitoring AccessHomelab
42. Designing Homelab
43. Building Homelab
44. Testing Homelab
45. Failure Points Homelab
46. Redundancies HomelabLibre
47. Failure Points Libre
48. Redundancies LibreComponent Audit
49. List all Components
50. Fail Check Each Component
51. Redundancy / Backup / Manual Backup for each component failurePotential Failures
52. ISP Failure
53. Router/Modem Failure
54. Server Failure
55. Phone Failure
56. Redundant Bluetooth Libre to Server Connection
57. Libre Fails or is removed
58. Benny doesn't wake up
59. Mechanical Failure on Dispensation
60. Power OUtage
61. Default Rescue Mode
62. Regardless of what fails or how, default to feeding food/rescue reiably.
63. Need Camera to Veify it's ***Benny*** who eats his foo
64. Dogs get into food early
65. PI Compatibility Check
66. Make sure the project is still capable of running on pi + pi venv cleanup
67. SSH Disconnect Issue with PI
68. Plug Camera into PI
69. Write something to see camera images from P
70. PI Camera Testing
71. Let's look at the dev.md for testing and redundancy criteria - should help other projects as well
72. Fix up this Document




### Server Driver

23

### Honey Drop Rescue

Server Brains, Server Driver ~ 18

### Verification station (camera)

Server Brains and Driver - 10

### Kibble Autofeeder Bowl

10

### Deadman's Switch and Watchdog Circuit Redundancies

Honey Drop ~ 8

### Honey drop rescue alert

7

### Kibble Autofeeder Alert

7

### Kibble Autofeeder Serving Mechanism

Brains, Driver, Bowl ~6

### Training process

Alerts ~ 6

### Server LLU Subversion BLE Direct Hack

4
