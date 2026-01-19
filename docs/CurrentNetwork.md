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
    Phone["Phone (Libre App)"]
    WatchGDH["Watch GDH"]
    PhoneGDH["Phone GDH"]
    GDH["GlucoDataHandler"]
 end

  %% ---------- MANUAL ----------
  subgraph MANUAL["Manual"]
    James
  end

  %% ---------- FAILURE ----------
  subgraph FAILURE["Failure"]
    SignalLoss
    SignalError
    PowerLoss
    Damage
    Expiration
  end

  %% =========================
  %% Primary data path: glucose -> decision
  %% =========================
  Libre -->|Libre Data over BLE| Phone
  Libre -.-> Damage
  Libre -.-> SignalLoss
  Libre -.-> Expiration

  Phone -->|Libre Data over Wi-Fi or Cellular| LLU
  Phone -.->PowerLoss
  Phone -.->SignalLoss
  LLU --> GDH
  GDH --> PhoneGDH
  GDH --> WatchGDH
  ```
