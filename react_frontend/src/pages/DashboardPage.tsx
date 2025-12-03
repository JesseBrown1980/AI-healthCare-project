import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDashboardPatients } from '../api'
import type { DashboardPatient } from '../api/types'
import './DashboardPage.css'

const severityOrder = ['critical', 'high', 'medium', 'low', 'info', 'unknown']

const formatSeverity = (severity?: string) => {
  if (!severity) return 'Unknown'
  const normalized = severity.toLowerCase()
  return normalized.charAt(0).toUpperCase() + normalized.slice(1)
}

const getSeverityRank = (severity?: string) => {
  const normalized = severity?.toLowerCase() ?? 'unknown'
  const index = severityOrder.indexOf(normalized)
  return index === -1 ? severityOrder.length : index
}

const DashboardPage = () => {
  const [patients, setPatients] = useState<DashboardPatient[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [severityFilter, setSeverityFilter] = useState('all')
  const [specialtyFilter, setSpecialtyFilter] = useState('all')
  const [sortBy, setSortBy] = useState<'severity' | 'risk' | 'name'>('severity')

  const navigate = useNavigate()

  useEffect(() => {
    const fetchPatients = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await getDashboardPatients()
        setPatients(data)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load patients'
        setError(message)
      } finally {
        setLoading(false)
      }
    }

    void fetchPatients()
  }, [])

  const specialties = useMemo(() => {
    const unique = new Set<string>()
    patients.forEach((patient) => {
      if (patient.specialty) {
        unique.add(patient.specialty)
      }
    })
    return Array.from(unique)
  }, [patients])

  const filteredPatients = useMemo(() => {
    return patients
      .filter((patient) => {
        const matchesSeverity =
          severityFilter === 'all' || patient.highest_alert_severity?.toLowerCase() === severityFilter
        const matchesSpecialty =
          specialtyFilter === 'all' || patient.specialty?.toLowerCase() === specialtyFilter
        return matchesSeverity && matchesSpecialty
      })
      .sort((a, b) => {
        if (sortBy === 'severity') {
          return getSeverityRank(a.highest_alert_severity) - getSeverityRank(b.highest_alert_severity)
        }
        if (sortBy === 'risk') {
          return (b.latest_risk_score ?? 0) - (a.latest_risk_score ?? 0)
        }
        return (a.name ?? a.patient_id).localeCompare(b.name ?? b.patient_id)
      })
  }, [patients, severityFilter, specialtyFilter, sortBy])

  const renderContent = () => {
    if (loading) {
      return <div className="dashboard__state">Loading patients…</div>
    }

    if (error) {
      return <div className="dashboard__state dashboard__state--error">{error}</div>
    }

    if (!filteredPatients.length) {
      return <div className="dashboard__state">No patients found.</div>
    }

    return (
      <div className="dashboard__table" role="table">
        <div className="dashboard__row dashboard__row--header" role="row">
          <div className="dashboard__cell" role="columnheader">
            Patient
          </div>
          <div className="dashboard__cell" role="columnheader">
            Specialty
          </div>
          <div className="dashboard__cell" role="columnheader">
            Severity
          </div>
          <div className="dashboard__cell" role="columnheader">
            Main Risk Score
          </div>
          <div className="dashboard__cell" role="columnheader">
            Action
          </div>
        </div>
        {filteredPatients.map((patient) => {
          const severity = patient.highest_alert_severity?.toLowerCase() ?? 'unknown'
          return (
            <div className="dashboard__row" role="row" key={patient.patient_id}>
              <div className="dashboard__cell" role="cell">
                <div className="dashboard__title">{patient.name ?? 'Unknown patient'}</div>
                <div className="dashboard__subtitle">ID: {patient.patient_id}</div>
              </div>
              <div className="dashboard__cell" role="cell">
                {patient.specialty ?? 'Not specified'}
              </div>
              <div className="dashboard__cell" role="cell">
                <span className={`severity-badge severity-badge--${severity}`}>
                  {formatSeverity(patient.highest_alert_severity)}
                </span>
              </div>
              <div className="dashboard__cell" role="cell">
                {patient.latest_risk_score?.toFixed(2) ?? '—'}
              </div>
              <div className="dashboard__cell" role="cell">
                <button
                  className="dashboard__button"
                  type="button"
                  onClick={() => navigate(`/patient/${patient.patient_id}`)}
                >
                  View patient
                </button>
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <section className="page dashboard">
      <div className="dashboard__header">
        <div>
          <h1>Patient Dashboard</h1>
          <p className="dashboard__description">
            Overview of patients with their latest risk scores and alert severities.
          </p>
        </div>
        <div className="dashboard__controls">
          <label className="dashboard__control">
            <span>Severity</span>
            <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
              <option value="all">All</option>
              {severityOrder.map((severity) => (
                <option key={severity} value={severity}>
                  {formatSeverity(severity)}
                </option>
              ))}
            </select>
          </label>
          <label className="dashboard__control">
            <span>Specialty</span>
            <select value={specialtyFilter} onChange={(e) => setSpecialtyFilter(e.target.value)}>
              <option value="all">All</option>
              {specialties.map((specialty) => (
                <option key={specialty} value={specialty.toLowerCase()}>
                  {specialty}
                </option>
              ))}
            </select>
          </label>
          <label className="dashboard__control">
            <span>Sort by</span>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as typeof sortBy)}>
              <option value="severity">Severity</option>
              <option value="risk">Risk score</option>
              <option value="name">Name</option>
            </select>
          </label>
        </div>
      </div>
      {renderContent()}
    </section>
  )
}

export default DashboardPage
