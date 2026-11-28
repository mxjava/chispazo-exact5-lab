#!/usr/bin/env python3
"""Static audit of public SICAL/access procedures and the V265 claim guard."""
from __future__ import annotations
import ast, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/evidence/V265_SICAL_ACCESS_MONITORING_20261128.md'
V265=ROOT/'src/v265/CHISPAZO_V265_PHYSICAL_METADATA_EVALUATOR.py'
ANCHORS={
 'restricted_area_scope':'áreas restringidas de la Gerencia de Sorteos',
 'visitor_log_fields':'hora de entrada, nombre completo, persona visitada, objeto de la visita',
 'access_card_nontransferable':'personales e intransferibles',
 'sgaf_int48_revision':'revisión 08 (marzo de 2026)',
 'clásico_next_day_md5':'Para el sorteo de las 21:00, el procedimiento indica que esa copia al servidor de contingencia se realiza al día siguiente',
 'md5_not_e_signature':'no debe llamarse firma electrónica',
 'sto18_not_cs18':'STO-18 no es CS-18',
 'ca01_hourly':'CA-01, Registro Diario de Ventas',
 'ca02_half_hour':'CA-02, Registro Diario de Comunicaciones',
 'ca04_after_resolution':'se registra después de que el incidente se soluciona',
 'ca06_interfaces':'CA-06, Informe de Interfaces',
 'mjf_interface':'MJF, archivos técnicos, comunicaciones y logs del sistema',
 'no_draw_machine_scope':'No son incidencias de la máquina de extracción, estuches ni esferas',
 'no_raw_logs':'No se obtuvieron registros reales por concurso',
}
def fn(tree,name):
 for n in tree.body:
  if isinstance(n,ast.FunctionDef) and n.name==name:return n
 raise AssertionError(name)
def ret_dict(f):
 for n in ast.walk(f):
  if isinstance(n,ast.Return) and isinstance(n.value,ast.Dict):return ast.literal_eval(n.value)
 raise AssertionError('guard dict')
def req_fields(src):
 tree=ast.parse(src)
 for n in ast.walk(fn(tree,'main')):
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='req_m' for t in n.targets):return ast.literal_eval(n.value)
 raise AssertionError('req_m')
def build_report():
 doc=DOC.read_text(encoding='utf-8'); anchors={k:v in doc for k,v in ANCHORS.items()}
 src=V265.read_text(encoding='utf-8'); guard=ret_dict(fn(ast.parse(src),'physical_evidence_guard'))
 fields=req_fields(src)
 return {
  'audit_id':'V265_SICAL_ACCESS_MONITORING_20261128',
  'classification':'DOCUMENTED_MECHANISM_ONLY',
  'all_anchors_pass':all(anchors.values()),'anchors':anchors,
  'official_records':{
   'sgaf_pro_95_access_fields':['entry_time','full_name','visited_person','purpose','entity_company','exit_time','visitor_signature','visited_person_signoff'],
   'sgaf_int_48_classic_md5_copy':'next_day_after_21_00_close',
   'md5_is_electronic_signature':False,
   'sgaf_pro_47_logs':['CA-01','CA-02','CA-04','CA-05','CA-06','MJF/interface/system logs'],
   'ca04_recorded_after_resolution':True,
   'these_are_draw_machine_telemetry':False,
  },
  'v265':{
   'required_metadata_fields':fields,
   'source_provenance_required':guard['source_provenance_required'],
   'physical_bias_evidence':guard['physical_bias_evidence'],
   'actionable_for_betting':guard['actionable_for_betting'],
   'per_sphere_weights_consumed':guard['per_sphere_weights_consumed'],
   'per_sphere_rfid_mapping_consumed':guard['per_sphere_rfid_mapping_consumed'],
   'extraction_order_consumed':guard['extraction_order_consumed'],
   'per_extraction_timestamps_consumed':guard['per_extraction_timestamps_consumed'],
   'anytime_evalue_gate_implemented':guard['anytime_evalue_gate_implemented'],
  },
  'analysis':{'type':'PUBLIC_PROCEDURE_STATIC_CROSSWALK_AND_V265_AST_AUDIT','uses_draw_outcomes':False,'uses_synthetic_records':False,'uses_authentic_draw_level_logs':False,'statistical_tests_run':[],'oos_gate_passed':False,'multiplicity_gate_passed':False,'anytime_evalue_gate_passed':False},
  'preservation':{'canonical_history_touched':False,'v294_touched':False,'main_written':False,'merge_or_promotion':False}
 }
if __name__=='__main__':print(json.dumps(build_report(),ensure_ascii=False,indent=2,sort_keys=True))
