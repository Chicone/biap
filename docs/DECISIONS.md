# Engineering Decisions

---

## 2026-06-29

### Project Philosophy

BIAP is designed as a scientific AI platform rather than a simple image analysis dashboard.

Reason:

The objective is to demonstrate modern AI software engineering practices similar to those used in pharmaceutical research and AI-for-science organisations.

---

## 2026-06-29

### Central Object

The central object of BIAP is an Experiment rather than an Image.

Reason:

An experiment naturally groups:

- images
- metadata
- segmentations
- measurements
- models
- reports

This better reflects real laboratory workflows.

---

## 2026-06-29

### AI Strategy

The project will progressively integrate:

Computer Vision
→ Classical ML
→ Deep Learning
→ Graph Neural Networks
→ Large Language Models
→ Agentic AI

Reason:

Each stage builds naturally upon the previous one while demonstrating progressively more advanced AI methodologies.