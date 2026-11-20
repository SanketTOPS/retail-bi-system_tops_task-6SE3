/**
 * src/pages/Profile.jsx
 * ─────────────────────
 * Business Profile Management Page.
 *
 * Supports creating and updating the company's retail profile:
 *  - Company Name, Industry, Description
 *  - Team Size, Founded Year
 *  - Interactive Business Goals tag system
 *  - Contact information (City, Country, Website, Phone)
 */

import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { getProfileApi, createProfileApi, updateProfileApi } from '@/api/profile';

const INDUSTRY_OPTIONS = [
  'Retail',
  'Fashion & Apparel',
  'Grocery & Supermarket',
  'Consumer Electronics',
  'Home & Furniture',
  'Health & Beauty',
  'Department Store',
  'Omnichannel Commerce',
  'Other',
];

const SUGGESTED_GOALS = [
  'Increase gross margin by 15%',
  'Automate inventory reorder points to prevent stockouts',
  'Improve repeat customer purchase frequency',
  'Reduce product return rates below 3%',
  'Optimize marketing channel ROAS across campaigns',
];

export default function Profile() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isExisting, setIsExisting] = useState(false);

  const [form, setForm] = useState({
    company_name: '',
    industry: 'Retail',
    description: '',
    team_size: '',
    founded_year: '',
    city: '',
    country: 'India',
    website: '',
    phone: '',
    logo_url: '',
    business_goals: [],
  });

  const [goalInput, setGoalInput] = useState('');
  const [errors, setErrors] = useState({});

  // ── 1. Fetch Profile on Mount ──────────────────────────────────────────────
  useEffect(() => {
    async function loadProfile() {
      setLoading(true);
      try {
        const profile = await getProfileApi();
        if (profile) {
          setIsExisting(true);
          setForm({
            company_name: profile.company_name || '',
            industry: profile.industry || 'Retail',
            description: profile.description || '',
            team_size: profile.team_size ? String(profile.team_size) : '',
            founded_year: profile.founded_year ? String(profile.founded_year) : '',
            city: profile.city || '',
            country: profile.country || 'India',
            website: profile.website || '',
            phone: profile.phone || '',
            logo_url: profile.logo_url || '',
            business_goals: Array.isArray(profile.business_goals) ? profile.business_goals : [],
          });
        }
      } catch (err) {
        toast.error('Failed to load business profile.');
      } finally {
        setLoading(false);
      }
    }
    loadProfile();
  }, []);

  // ── 2. Field Change Handlers ───────────────────────────────────────────────
  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }));
    }
  };

  // ── 3. Business Goals Tag Management ───────────────────────────────────────
  const addGoal = (goalText) => {
    const cleaned = (goalText || goalInput).trim();
    if (!cleaned) return;
    if (form.business_goals.includes(cleaned)) {
      toast.error('Goal is already added.');
      return;
    }
    setForm((prev) => ({
      ...prev,
      business_goals: [...prev.business_goals, cleaned],
    }));
    setGoalInput('');
  };

  const removeGoal = (index) => {
    setForm((prev) => ({
      ...prev,
      business_goals: prev.business_goals.filter((_, i) => i !== index),
    }));
  };

  const handleGoalKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addGoal();
    }
  };

  // ── 4. Validation ──────────────────────────────────────────────────────────
  const validate = () => {
    const newErrors = {};
    if (!form.company_name.trim() || form.company_name.trim().length < 2) {
      newErrors.company_name = 'Company name must be at least 2 characters.';
    }
    if (form.team_size && Number(form.team_size) <= 0) {
      newErrors.team_size = 'Team size must be greater than 0.';
    }
    if (form.founded_year) {
      const year = Number(form.founded_year);
      if (year < 1800 || year > 2050) {
        newErrors.founded_year = 'Founded year must be between 1800 and 2050.';
      }
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // ── 5. Submit Handler ──────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setSaving(true);
    const payload = {
      company_name: form.company_name.trim(),
      industry: form.industry,
      description: form.description.trim() || null,
      team_size: form.team_size ? parseInt(form.team_size, 10) : null,
      founded_year: form.founded_year ? parseInt(form.founded_year, 10) : null,
      city: form.city.trim() || null,
      country: form.country.trim() || 'India',
      website: form.website.trim() || null,
      phone: form.phone.trim() || null,
      logo_url: form.logo_url.trim() || null,
      business_goals: form.business_goals.length > 0 ? form.business_goals : null,
    };

    try {
      if (isExisting) {
        await updateProfileApi(payload);
        toast.success('Business profile updated successfully!');
      } else {
        await createProfileApi(payload);
        setIsExisting(true);
        toast.success('Business profile created successfully!');
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to save business profile.';
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSaving(false);
    }
  };

  // ── Render Loading State ───────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="page-wrapper">
        <div className="page-header">
          <h2 className="page-header__title">Business Profile</h2>
          <p className="page-header__sub">Loading company details...</p>
        </div>
        <div className="card loading-card">
          <div className="spinner spinner--lg" />
          <p className="loading-text">Fetching profile...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div className="page-header__row">
          <div>
            <h2 className="page-header__title">Business Profile & Domain Rules</h2>
            <p className="page-header__sub">
              Define your enterprise identity, industry sector, and strategic performance targets.
              The AI Strategy and Verification agents tailor their insights to your goals.
            </p>
          </div>
          <span className={`status-pill ${isExisting ? 'status-pill--active' : 'status-pill--pending'}`}>
            {isExisting ? '● Profile Configured' : '○ Not Configured'}
          </span>
        </div>
      </div>

      <form className="profile-form card" onSubmit={handleSubmit} noValidate>
        {/* Section 1: Basic Identity */}
        <div className="form-section">
          <h3 className="form-section__title">Enterprise Identity</h3>
          <p className="form-section__desc">Basic organizational parameters used across generated executive dossiers.</p>

          <div className="form-grid form-grid--2">
            <div className={`form-group ${errors.company_name ? 'form-group--error' : ''}`}>
              <label className="form-label" htmlFor="company_name">
                Company / Store Name <span className="req">*</span>
              </label>
              <input
                id="company_name"
                name="company_name"
                type="text"
                className="form-input"
                placeholder="e.g. RetailPulse MegaStore"
                value={form.company_name}
                onChange={handleChange}
              />
              {errors.company_name && <p className="form-error">{errors.company_name}</p>}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="industry">Industry Sector</label>
              <select
                id="industry"
                name="industry"
                className="form-input"
                value={form.industry}
                onChange={handleChange}
              >
                {INDUSTRY_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="description">Business Scope & Description</label>
            <textarea
              id="description"
              name="description"
              rows={3}
              className="form-input form-textarea"
              placeholder="Brief summary of business model, physical footprint, and target demographic..."
              value={form.description}
              onChange={handleChange}
            />
          </div>

          <div className="form-grid form-grid--2">
            <div className={`form-group ${errors.team_size ? 'form-group--error' : ''}`}>
              <label className="form-label" htmlFor="team_size">Team Size (Employees)</label>
              <input
                id="team_size"
                name="team_size"
                type="number"
                min="1"
                className="form-input"
                placeholder="e.g. 50"
                value={form.team_size}
                onChange={handleChange}
              />
              {errors.team_size && <p className="form-error">{errors.team_size}</p>}
            </div>

            <div className={`form-group ${errors.founded_year ? 'form-group--error' : ''}`}>
              <label className="form-label" htmlFor="founded_year">Founded Year</label>
              <input
                id="founded_year"
                name="founded_year"
                type="number"
                min="1800"
                max="2050"
                className="form-input"
                placeholder="e.g. 2018"
                value={form.founded_year}
                onChange={handleChange}
              />
              {errors.founded_year && <p className="form-error">{errors.founded_year}</p>}
            </div>
          </div>
        </div>

        {/* Section 2: Strategic Business Goals */}
        <div className="form-section">
          <h3 className="form-section__title">Strategic Targets & KPIs</h3>
          <p className="form-section__desc">
            Define objectives for the multi-agent system. Strategy agents will measure performance against these targets.
          </p>

          <div className="goals-input-box">
            <div className="goals-input-row">
              <input
                type="text"
                className="form-input"
                placeholder="Type a goal and press Enter (or click Add)..."
                value={goalInput}
                onChange={(e) => setGoalInput(e.target.value)}
                onKeyDown={handleGoalKeyDown}
              />
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => addGoal()}
              >
                + Add Goal
              </button>
            </div>

            {/* Quick suggestions */}
            <div className="goals-suggestions">
              <span className="goals-suggestions__label">Quick add suggestions:</span>
              <div className="goals-suggestions__list">
                {SUGGESTED_GOALS.map((sug, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="chip chip--suggestion"
                    onClick={() => addGoal(sug)}
                  >
                    + {sug}
                  </button>
                ))}
              </div>
            </div>

            {/* Active Goals Tags */}
            <div className="goals-tag-container">
              {form.business_goals.length === 0 ? (
                <p className="empty-goals-hint">No specific goals added yet. Add targets above or pick from suggestions.</p>
              ) : (
                form.business_goals.map((goal, idx) => (
                  <div key={idx} className="chip chip--active">
                    <span>🎯 {goal}</span>
                    <button
                      type="button"
                      className="chip__remove"
                      onClick={() => removeGoal(idx)}
                      aria-label="Remove goal"
                    >
                      ×
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Section 3: Contact & Presence */}
        <div className="form-section">
          <h3 className="form-section__title">Contact & Web Presence</h3>
          <div className="form-grid form-grid--2">
            <div className="form-group">
              <label className="form-label" htmlFor="city">Headquarters City</label>
              <input
                id="city"
                name="city"
                type="text"
                className="form-input"
                placeholder="e.g. Bengaluru"
                value={form.city}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="country">Country</label>
              <input
                id="country"
                name="country"
                type="text"
                className="form-input"
                placeholder="e.g. India"
                value={form.country}
                onChange={handleChange}
              />
            </div>
          </div>

          <div className="form-grid form-grid--2">
            <div className="form-group">
              <label className="form-label" htmlFor="website">Website URL</label>
              <input
                id="website"
                name="website"
                type="url"
                className="form-input"
                placeholder="https://example.com"
                value={form.website}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="phone">Phone Number</label>
              <input
                id="phone"
                name="phone"
                type="tel"
                className="form-input"
                placeholder="+91-9876543210"
                value={form.phone}
                onChange={handleChange}
              />
            </div>
          </div>
        </div>

        {/* Form Actions */}
        <div className="form-actions">
          <button
            type="submit"
            className="btn btn--primary btn--save"
            disabled={saving}
          >
            {saving ? (
              <>
                <span className="spinner" /> Saving Profile...
              </>
            ) : isExisting ? (
              'Save Profile Changes'
            ) : (
              'Create Business Profile'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
