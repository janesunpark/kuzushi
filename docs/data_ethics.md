# Data Ethics & Anonymization

## Purpose

This document explains the privacy and ethics principles used in Kuzushi. Because the project involves observations of young learners in academic enrichment and embodied learning contexts, all public-facing materials are written with strict attention to anonymity, privacy, and responsible interpretation.

## Data Collection Context

Kuzushi is based on structured observation logs from small-group academic enrichment sessions, with periodic observations from embodied movement contexts such as youth Jiu Jitsu classes. Observations focus on learning behaviors such as task persistence, strategy selection, frustration recovery, co-regulation, motivation, spatial reasoning, and engagement patterns.

All observations are collected with parental consent. The project is observational and exploratory; it is not designed to diagnose, rank, evaluate, or label individual learners.

## Private Materials

The following materials remain private and are not included in this repository:

* raw session observation logs
* learner names or family-identifying details
* exact dates, times, and locations
* videos, photos, or other media
* private notes about emotional, social, or family context
* sensitive child-specific details that could increase identifiability

## Public Materials

Public-facing materials are distilled from private observation logs and weekly synthesis notes. These materials are anonymized and written at the level of broader learning patterns rather than identifiable individual records. 

Learners are referenced only through anonymized labels. Published examples are edited to preserve the relevant learning behavior while reducing unnecessary detail that could identify a learner, family, school, academy, or training context. 

## Anonymization Principles

Kuzushi uses the following principles when preparing public-facing materials:

* remove names and identifying details
* avoid exact dates, locations, and schedules
* avoid unnecessary family or school context
* generalize sensitive or highly specific incidents
* describe patterns rather than private child-level narratives
* avoid publishing raw dialogue unless it is brief, relevant, and non-identifying
* avoid sharing media, images, or video
* treat all public examples as illustrative, not diagnostic

## Interpretation Boundaries

Kuzushi is an exploratory observational project. Public notes should not be interpreted as formal research findings, clinical assessments, educational evaluations, or evidence of causal relationships.

The project does not claim that participation in Jiu Jitsu causes academic improvement, nor does it claim that observed patterns prove transfer between embodied and academic domains. Cross-context observations are treated as exploratory signals that may help generate future research questions.

## Use of Derived Data

Future technical work may involve derived, anonymized data structures based on private observation logs. Any derived data used for public analysis will be designed to reduce identifiability and will focus on broad patterns such as task type, engagement, scaffolding, strategy shifts, or recovery patterns.

Raw observation logs and sensitive private data will not be published.

## What This Repository Publishes

Kuzushi publishes two things: what the pipeline does, demonstrated on synthetic data, and what the observer noticed, described in words as patterns. It does not publish the measurement record: no real per-learner ratings, counts, or dates, whether in data, figures, or source code.

The synthetic data generator keeps the shape of each learner's data (which ratings are common and which are rare, and how the two learners differ) but not the real counts. Figures made from synthetic data show that the pipeline recovers patterns the generator was built to contain; they are not findings about the learners.

Two kinds of real facts are kept on purpose. Counts that describe how much work the project involved, such as the number of sessions and weekly notes, stay close to the real ones, because changing them would misstate the project's scope. The weeks in which the observation form itself changed are published at week level, because they describe the instrument, not a learner.

## Responsible Use

This repository is shared for documentation, portfolio, and academic review purposes only. The materials should not be reused, redistributed, or adapted as child-level assessment tools without permission.

The purpose of Kuzushi is to document learning patterns responsibly while protecting the privacy, dignity, and developmental context of the learners observed.