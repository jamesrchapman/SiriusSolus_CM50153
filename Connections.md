# Connections

## Next

We're mapping failure modes to the FAIL node (SPF)

Once we develop a redundancy for the failure mode, they'll map that particularly failure to whatever redundancy instead of the SPF.

```mermaid
flowchart LR
  %% =========================
  %% Solus for Benny — Topology + Redundancy + SPFs
  %% Legend:
  %%   Solid  = primary path
  %%   Dashed = failure/backup path
  %% =========================

  %% ---------- SENSING ----------
  subgraph SENSING["Sensing (Glucose)"]
    Libre["Libre Sensor"]

  end

  %% ---------- RELAY ----------
  subgraph RELAY["Relay / Cloud "]
    LLU["LibreLinkUp"]
    PhoneLibre["Phone (Libre App)"]
    WatchGDH["Watch GDH"]
    PhoneGDH["Phone GDH"]
    PiBlue["Pi Bluetooth"]
    GDH["GlucoDataHandler"]
 end

  %% ---------- CONTROL ----------
  subgraph CONTROL["Control / Decision"]
    Pi["Solus Pi Controller"]
    PiHoneyTrigger["Pi Honey Controller"]
    Pi2["Failover Pi (optional)"]
    Watchdog["HW/Timer Watchdog"]
    PiAlert["Pi Alert James"]
    NoLibreSignaltoPi["No New Data"]
  end

  %% ---------- MANUAL ----------
  subgraph MANUAL["Manual"]
    James
  end

  %% ---------- FAILURE ----------
  subgraph FAILURE["Failure"]
    FAIL["SPF"]
    POWERLOSS
    CONNECTIONLOSS
  end

  %% =========================
  %% Primary data path: glucose -> decision
  %% =========================
  Libre -->|BLE| PhoneLibre
  Libre -->|BLE| PiBlue
  Libre -->|Torn Off| NoLibreSignaltoPi
  Libre -->|Out of Bluetooth Range| NoLibreSignaltoPi
  Libre -->|Expiration| NoLibreSignaltoPi

  NoLibreSignaltoPi -->|Too Long| PiHoneyTrigger
  NoLibreSignaltoPi -->|Too Long| PiAlert

  PhoneLibre -->|Internet HTTPS| LLU
  PhoneLibre -->|Dies| PiBlue
  PhoneLibre -->|Alerts| WatchLibreAlert
  WatchLibreAlert-->James
  LLU -->|Internet HTTPS| Pi
  LLU -->|Down Highly Unlikely|FAIL
  LLU --> GDH
  GDH --> PhoneGDH
  GDH --> WatchGDH
  PiBlue -->|Direct| Pi
  ```

  %% Home network dependency
  PhoneLibre -->|Wi-Fi| AP
  Pi -->|Ethernet/Wi-Fi| AP
  AP --> ISP
  ISP --> LLU

  %% =========================
  %% Backup glucose path (if you have one)
  %% =========================
  PhoneLibre -.->|Local export or API if possible| Pi

  %% =========================
  %% Decision -> actuation path
  %% =========================
  Pi -->|LAN MQTT/HTTP| FeederMCU
  FeederMCU -->|GPIO/PWM| Actuator
  Actuator --> Chute --> Bowl

  %% Failover controller path
  Pi2 -.->|LAN takeover| FeederMCU
  Pi2 -.->|poll cloud| LLU

  %% Watchdog recovery
  Watchdog -->|reset| Pi
  Watchdog -->|reset| FeederMCU

  %% =========================
  %% Verification paths
  %% =========================
  Camera -->|RTSP snapshot| Pi
  Weight -->|delta grams| Pi
  Switch -->|movement pulses| Pi

  %% =========================
  %% Alerts
  %% =========================
  Pi -->|push| Push --> You
  Pi -.->|SMS| SMS --> You
  Pi -.->|local| Siren

  %% =========================
  %% Manual override
  %% =========================
  You -.-> ManualFeed -.-> Bowl

  %% =========================
  %% Power dependencies
  %% =========================
  Mains --> UPS
  UPS --> AP
  UPS --> Pi
  UPS --> FeederMCU
  Batt -.-> FeederMCU

  %% Optional: camera on UPS
  UPS -.-> Camera
