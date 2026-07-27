# -*- coding: utf-8 -*-
# EDE 파서 자동 생성 — LMV-D3-MOD_V3_0_8_EDE_File.CSV (Belimo, 2025-04-25)
BELIMO_EDE_POINTS = [
 {
  "inst": 1,
  "type": "AI",
  "unitDisp": "%",
  "name": "RelPos · 댐퍼 상대 개도",
  "note": "Relative Position in %"
 },
 {
  "inst": 2,
  "type": "AI",
  "unitDisp": "°",
  "name": "AbsPos · 댐퍼 절대 위치",
  "note": "Absolute Position in degree or mm"
 },
 {
  "inst": 6,
  "type": "AI",
  "unitDisp": "%",
  "name": "SpAnalog · 아날로그 설정값",
  "note": "Analog Setpoint in %"
 },
 {
  "inst": 10,
  "type": "AI",
  "unitDisp": "%",
  "name": "RelFlow · 상대 풍량",
  "note": "Relative Flow in %"
 },
 {
  "inst": 19,
  "type": "AI",
  "unitDisp": "L/s",
  "name": "AbsFlow_UnitSel · 절대 풍량",
  "note": "Absolute Flow in selected unit"
 },
 {
  "inst": 20,
  "type": "AI",
  "unitDisp": "—",
  "name": "Sens1Analog · 센서1 아날로그 값",
  "note": "Sensor 1 as analog value"
 },
 {
  "inst": 1,
  "type": "AO",
  "unitDisp": "%",
  "name": "SpRel · 풍량 지령(상대 설정값)",
  "note": "Relative Setpoint in % · 쓰기 가능"
 },
 {
  "inst": 97,
  "type": "AV",
  "unitDisp": "%",
  "name": "Min · 최소 풍량 V'min",
  "note": "Min Setpoint in %"
 },
 {
  "inst": 98,
  "type": "AV",
  "unitDisp": "%",
  "name": "Max · 최대 풍량 V'max",
  "note": "Max Setpoint in %"
 },
 {
  "inst": 104,
  "type": "AV",
  "unitDisp": "L/s",
  "name": "Vnom_UnitSel · 정격 풍량 V'nom",
  "note": "Nominal Flow in [UnitSel]"
 },
 {
  "inst": 130,
  "type": "AV",
  "unitDisp": "s",
  "name": "BusWatchdog · 통신 감시 시간",
  "note": "Timeout for Bus Watchdog in s"
 },
 {
  "inst": 20,
  "type": "BI",
  "unitDisp": "—",
  "name": "Sens1Switch · 센서1 접점",
  "note": "Sensor 1 as Switch · Inactive / Active"
 },
 {
  "inst": 99,
  "type": "BI",
  "unitDisp": "—",
  "name": "BusTermination · 종단저항 120Ω",
  "note": "Bus Termination · Disabled / Enabled"
 },
 {
  "inst": 101,
  "type": "BI",
  "unitDisp": "—",
  "name": "SummaryStatus · 종합 상태",
  "note": "Summary Status · OK / Not OK"
 },
 {
  "inst": 100,
  "type": "MSI",
  "unitDisp": "—",
  "name": "InternalActivity · 내부 동작",
  "note": "Internal Activity · None / Test / Adaption"
 },
 {
  "inst": 106,
  "type": "MSI",
  "unitDisp": "—",
  "name": "StatusActuator · 액추에이터 상태",
  "note": "Status Actuator · OK / Actuator cannot move / Gear disengaged / Mechanical travel increased"
 },
 {
  "inst": 110,
  "type": "MSI",
  "unitDisp": "—",
  "name": "StatusDevice · 장치 상태",
  "note": "Status Device · OK / BusWatchdog triggered"
 },
 {
  "inst": 1,
  "type": "MSO",
  "unitDisp": "—",
  "name": "Override · 강제 제어",
  "note": "Override Control · None / Open / Close / Min_Vmin / Mid_Vmid / Max_Vmax · 쓰기 가능"
 },
 {
  "inst": 120,
  "type": "MSV",
  "unitDisp": "—",
  "name": "Command · 기능 지령",
  "note": "Initiate Function · None / Adaption / Test / Reset"
 },
 {
  "inst": 121,
  "type": "MSV",
  "unitDisp": "—",
  "name": "UnitSelFlow · 풍량 단위 선택",
  "note": "Unit Selection Flow · [m3/s] / [m3/h] / [l/s] / [l/min] / [l/h] / [gpm] / [cfm]"
 },
 {
  "inst": 122,
  "type": "MSV",
  "unitDisp": "—",
  "name": "SpSource · 설정값 소스",
  "note": "Setpoint Source · Analog / Bus"
 },
 {
  "inst": 123,
  "type": "MSV",
  "unitDisp": "—",
  "name": "ControlMode · 제어 모드",
  "note": "Control Mode · PosCtrl / FlowCtrl"
 },
 {
  "inst": 220,
  "type": "MSV",
  "unitDisp": "—",
  "name": "Sens1Type · 센서1 종류",
  "note": "Sensor 1 Type · None / Active / Passive_1K / Passive_20K / Switch / PT1000_C / NI1000_C / NTC10K_C / PT1000_F / NI1000_F / NTC10K_F"
 }
]
