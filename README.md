# Healthcare Agentic AI

A supervised Agentic AI research prototype for hospital discharge coordination.

## Project Goal

The project investigates whether a supervised agentic AI system can identify
discharge barriers and pending tasks, generate more complete discharge plans,
and follow human-approval and policy constraints.

## Initial Architecture

Patient Case JSON  
↓  
Input Reader  
↓  
Case Analyzer  
↓  
Barrier Detector + Task Detector  
↓  
Recommendation Generator  
↓  
Approval Gate + Policy Layer  
↓  
Output Composer  
↓  
Final Discharge Recommendation

An audit logger records intermediate actions and decisions throughout the
pipeline.

## Current Development Phase

The first prototype focuses on:

1. Input Reader
2. Case Analyzer
3. Barrier Detector

The system will initially be tested using synthetic patient discharge cases.

## Data Sources

The project will investigate the following PhysioNet resources:

- MIMIC-IV v3.1
- MIMIC-IV-Note v2.2
- MIMIC-IV-ED v2.2

Restricted MIMIC data will not be stored in this public repository.

## Synthetic Dataset

Initial synthetic patient cases include:

- diagnoses
- medications
- laboratory information
- discharge summaries
- pending tasks
- transportation status
- caregiver availability
- social barriers
- discharge workflow status

Cases are assigned standardized barrier and task IDs for reproducible
evaluation.

## Repository Structure

- `agents/` – Agent implementations
- `data/synthetic/` – Synthetic patient cases
- `data/preprocessing/` – Data preprocessing utilities
- `policy/` – Safety, policy, and approval controls
- `prompts/` – Agent prompt templates
- `evaluation/` – Evaluation scripts and metrics
- `notebooks/` – Exploratory analysis
- `tests/` – Unit and integration tests
- `results/` – Experimental outputs
- `docs/` – Project documentation

## Status

Architecture and evaluation taxonomy defined.

Synthetic case development and initial prototype implementation are in progress.
