import { describe, it, expect } from 'vitest'
import {
  PROPERTY_TYPE_LABELS,
  TYPOLOGY_OPTIONS,
  HEATING_OPTIONS,
  ENERGY_CLASSES,
  AMENITIES,
} from './property'

// Garde-fous sur le modèle « bien » fusionné (post-suppression de l'entité Unit).
// Ces invariants protègent contre les régressions de la refonte propriété/logement.

describe('PropertyType', () => {
  it("ne contient plus le type « immeuble »", () => {
    expect(Object.keys(PROPERTY_TYPE_LABELS)).not.toContain('immeuble')
  })

  it('expose exactement les 4 types retenus', () => {
    expect(Object.keys(PROPERTY_TYPE_LABELS).sort()).toEqual(
      ['appartement', 'autre', 'local_commercial', 'maison'],
    )
  })

  it('a un libellé non vide pour chaque type', () => {
    for (const label of Object.values(PROPERTY_TYPE_LABELS)) {
      expect(label.trim().length).toBeGreaterThan(0)
    }
  })
})

describe('Typologie', () => {
  it('va de T1 à T10', () => {
    expect(TYPOLOGY_OPTIONS).toEqual(['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10'])
  })
})

describe('DPE', () => {
  it('couvre les classes A à G + « non soumis » (NS)', () => {
    expect(ENERGY_CLASSES.map(c => c.value)).toEqual(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'NS'])
  })

  it('a des valeurs ≤ 2 caractères (contrainte colonne energy_class VARCHAR(2)) et des libellés non vides', () => {
    for (const c of ENERGY_CLASSES) {
      expect(c.value.length).toBeLessThanOrEqual(2)
      expect(c.label.trim().length).toBeGreaterThan(0)
    }
  })
})

describe('Chauffage — couverture du parc', () => {
  it('inclut fioul, bois/granulés et réseau urbain', () => {
    const values = HEATING_OPTIONS.map(h => h.value)
    expect(values).toContain('fioul')
    expect(values).toContain('bois_granules')
    expect(values).toContain('reseau_urbain')
  })

  it('a des valeurs ≤ 30 caractères (contrainte colonne heating_type VARCHAR(30))', () => {
    for (const h of HEATING_OPTIONS) {
      expect(h.value.length).toBeLessThanOrEqual(30)
    }
  })
})

describe('Chauffage', () => {
  it('propose des options avec value/label non vides', () => {
    expect(HEATING_OPTIONS.length).toBeGreaterThan(0)
    for (const h of HEATING_OPTIONS) {
      expect(h.value.length).toBeGreaterThan(0)
      expect(h.label.length).toBeGreaterThan(0)
    }
  })
})

describe('Équipements (AMENITIES)', () => {
  it('inclut la Fibre internet et la Climatisation', () => {
    const byKey = Object.fromEntries(AMENITIES.map(a => [a.key, a.label]))
    expect(byKey.has_fiber).toBe('Fibre internet')
    expect(byKey.has_air_conditioning).toBe('Climatisation')
  })

  it('a des clés uniques et des libellés non vides', () => {
    const keys = AMENITIES.map(a => a.key)
    expect(new Set(keys).size).toBe(keys.length)
    for (const a of AMENITIES) {
      expect(a.label.trim().length).toBeGreaterThan(0)
    }
  })

  it("toutes les clés sont des booléens du type Property (préfixe has_ ou champ équipement connu)", () => {
    const allowed = new Set([
      'furnished', 'kitchen_equipped', 'has_elevator', 'has_balcony',
      'has_terrace', 'has_garden', 'has_parking', 'has_cellar',
      'has_fiber', 'has_air_conditioning',
    ])
    for (const a of AMENITIES) {
      expect(allowed.has(a.key)).toBe(true)
    }
  })
})
