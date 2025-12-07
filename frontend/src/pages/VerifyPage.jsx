import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import './VerifyPage.css';

// Medical specialties list
const SPECIALTIES = [
    'Allergy and Immunology',
    'Anesthesiology',
    'Cardiology',
    'Dermatology',
    'Emergency Medicine',
    'Endocrinology',
    'Family Medicine',
    'Gastroenterology',
    'General Surgery',
    'Geriatric Medicine',
    'Hematology',
    'Infectious Disease',
    'Internal Medicine',
    'Nephrology',
    'Neurology',
    'Obstetrics and Gynecology',
    'Oncology',
    'Ophthalmology',
    'Orthopedic Surgery',
    'Otolaryngology (ENT)',
    'Pathology',
    'Pediatrics',
    'Physical Medicine and Rehabilitation',
    'Plastic Surgery',
    'Psychiatry',
    'Pulmonology',
    'Radiology',
    'Rheumatology',
    'Sports Medicine',
    'Urology',
    'Vascular Surgery',
];

// Insurance networks list
const INSURANCE_NETWORKS = [
    'Aetna',
    'Anthem Blue Cross',
    'Blue Cross Blue Shield',
    'Cigna',
    'Humana',
    'Kaiser Permanente',
    'Medicare',
    'Medicaid',
    'UnitedHealthcare',
    'Oscar Health',
    'Molina Healthcare',
    'Centene',
    'WellCare',
    'Magellan Health',
    'Tricare',
];

const VerifyPage = () => {
    const fileInputRef = useRef(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitResult, setSubmitResult] = useState(null);
    const [uploadedFiles, setUploadedFiles] = useState([]);

    const [formData, setFormData] = useState({
        // Identity fields (required)
        fullName: '',
        specialty: '',

        // Verify details (optional)
        address: '',
        phoneNumber: '',
        licenseNumber: '',
        insuranceNetworks: [],
        servicesOffered: '',
    });

    const [errors, setErrors] = useState({});

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
        // Clear error when user starts typing
        if (errors[name]) {
            setErrors(prev => ({ ...prev, [name]: '' }));
        }
    };

    const handleNetworkToggle = (network) => {
        setFormData(prev => ({
            ...prev,
            insuranceNetworks: prev.insuranceNetworks.includes(network)
                ? prev.insuranceNetworks.filter(n => n !== network)
                : [...prev.insuranceNetworks, network]
        }));
    };

    const handleFileUpload = (e) => {
        const files = Array.from(e.target.files);
        const validFiles = files.filter(file => {
            const isValid = file.type === 'application/pdf' ||
                file.type.startsWith('image/');
            const isUnderLimit = file.size <= 10 * 1024 * 1024; // 10MB limit
            return isValid && isUnderLimit;
        });

        setUploadedFiles(prev => [...prev, ...validFiles]);
    };

    const removeFile = (index) => {
        setUploadedFiles(prev => prev.filter((_, i) => i !== index));
    };

    const validateForm = () => {
        const newErrors = {};

        if (!formData.fullName.trim()) {
            newErrors.fullName = 'Full name is required';
        }

        if (!formData.specialty) {
            newErrors.specialty = 'Specialty is required';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!validateForm()) {
            return;
        }

        setIsSubmitting(true);
        setSubmitResult(null);

        try {
            const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

            // Create FormData for file upload
            const submitData = new FormData();
            submitData.append('fullName', formData.fullName);
            submitData.append('specialty', formData.specialty);
            submitData.append('address', formData.address);
            submitData.append('phoneNumber', formData.phoneNumber);
            submitData.append('licenseNumber', formData.licenseNumber);
            submitData.append('insuranceNetworks', JSON.stringify(formData.insuranceNetworks));
            submitData.append('servicesOffered', formData.servicesOffered);

            // Append files
            uploadedFiles.forEach((file, index) => {
                submitData.append(`documents`, file);
            });

            const response = await fetch(`${backendUrl}/api/verify`, {
                method: 'POST',
                body: submitData,
            });

            const result = await response.json();

            if (response.ok) {
                setSubmitResult({
                    success: true,
                    data: result
                });
            } else {
                setSubmitResult({
                    success: false,
                    error: result.message || 'Verification failed'
                });
            }
        } catch (error) {
            setSubmitResult({
                success: false,
                error: 'Unable to connect to the verification service. Please try again.'
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    const resetForm = () => {
        setFormData({
            fullName: '',
            specialty: '',
            address: '',
            phoneNumber: '',
            licenseNumber: '',
            insuranceNetworks: [],
            servicesOffered: '',
        });
        setUploadedFiles([]);
        setSubmitResult(null);
        setErrors({});
    };

    return (
        <div className="verify-page">
            <div className="verify-page__background">
                <div className="verify-page__glow verify-page__glow--1" />
                <div className="verify-page__glow verify-page__glow--2" />
            </div>

            <div className="verify-page__container">
                <motion.div
                    className="verify-page__header"
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    <div className="verify-page__icon">
                        <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="40" cy="40" r="36" stroke="url(#verifyGrad)" strokeWidth="4" strokeDasharray="8 4" />
                            <path
                                d="M40 20C28.95 20 20 28.95 20 40C20 51.05 28.95 60 40 60C51.05 60 60 51.05 60 40C60 28.95 51.05 20 40 20ZM36 50L26 40L28.82 37.18L36 44.34L51.18 29.16L54 32L36 50Z"
                                fill="url(#verifyGrad)"
                            />
                            <defs>
                                <linearGradient id="verifyGrad" x1="0" y1="0" x2="80" y2="80" gradientUnits="userSpaceOnUse">
                                    <stop stopColor="#1890ff" />
                                    <stop offset="1" stopColor="#13c2c2" />
                                </linearGradient>
                            </defs>
                        </svg>
                    </div>
                    <h1 className="verify-page__title">Provider Verification</h1>
                    <p className="verify-page__subtitle">
                        Enter provider details to validate against our AI-powered verification system
                    </p>
                </motion.div>

                <AnimatePresence mode="wait">
                    {submitResult ? (
                        <motion.div
                            key="result"
                            className="verify-page__result"
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            transition={{ duration: 0.3 }}
                        >
                            {submitResult.success ? (
                                <div className="result-card result-card--success">
                                    <div className="result-card__icon">✓</div>
                                    <h2>Verification Complete</h2>
                                    <p>The provider information has been verified successfully.</p>

                                    {submitResult.data && (
                                        <div className="result-card__data">
                                            <pre>{JSON.stringify(submitResult.data, null, 2)}</pre>
                                        </div>
                                    )}

                                    <div className="result-card__actions">
                                        <button onClick={resetForm} className="btn btn--primary">
                                            Verify Another Provider
                                        </button>
                                        <Link to="/" className="btn btn--ghost">
                                            Back to Home
                                        </Link>
                                    </div>
                                </div>
                            ) : (
                                <div className="result-card result-card--error">
                                    <div className="result-card__icon">!</div>
                                    <h2>Verification Failed</h2>
                                    <p>{submitResult.error}</p>

                                    <div className="result-card__actions">
                                        <button onClick={() => setSubmitResult(null)} className="btn btn--primary">
                                            Try Again
                                        </button>
                                        <Link to="/" className="btn btn--ghost">
                                            Back to Home
                                        </Link>
                                    </div>
                                </div>
                            )}
                        </motion.div>
                    ) : (
                        <motion.form
                            key="form"
                            className="verify-form"
                            onSubmit={handleSubmit}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            transition={{ duration: 0.4 }}
                        >
                            {/* Section 1: Identify */}
                            <div className="verify-form__section">
                                <div className="verify-form__section-header">
                                    <span className="verify-form__section-number">1</span>
                                    <div>
                                        <h2 className="verify-form__section-title">Identify Provider</h2>
                                        <p className="verify-form__section-subtitle">Required fields to identify the healthcare provider</p>
                                    </div>
                                </div>

                                <div className="verify-form__grid">
                                    <div className="form-group">
                                        <label htmlFor="fullName" className="form-label">
                                            Full Name <span className="required">*</span>
                                        </label>
                                        <input
                                            type="text"
                                            id="fullName"
                                            name="fullName"
                                            className={`form-input ${errors.fullName ? 'form-input--error' : ''}`}
                                            placeholder="Dr. John Smith, MD"
                                            value={formData.fullName}
                                            onChange={handleInputChange}
                                        />
                                        {errors.fullName && <span className="form-error">{errors.fullName}</span>}
                                    </div>

                                    <div className="form-group">
                                        <label htmlFor="specialty" className="form-label">
                                            Specialty <span className="required">*</span>
                                        </label>
                                        <select
                                            id="specialty"
                                            name="specialty"
                                            className={`form-select ${errors.specialty ? 'form-input--error' : ''}`}
                                            value={formData.specialty}
                                            onChange={handleInputChange}
                                        >
                                            <option value="">Select a specialty...</option>
                                            {SPECIALTIES.map(spec => (
                                                <option key={spec} value={spec}>{spec}</option>
                                            ))}
                                        </select>
                                        {errors.specialty && <span className="form-error">{errors.specialty}</span>}
                                    </div>
                                </div>
                            </div>

                            {/* Section 2: Verify Details */}
                            <div className="verify-form__section">
                                <div className="verify-form__section-header">
                                    <span className="verify-form__section-number">2</span>
                                    <div>
                                        <h2 className="verify-form__section-title">Verify Details</h2>
                                        <p className="verify-form__section-subtitle">Optional fields to validate provider information</p>
                                    </div>
                                </div>

                                <div className="verify-form__grid">
                                    <div className="form-group form-group--full">
                                        <label htmlFor="address" className="form-label">Address</label>
                                        <input
                                            type="text"
                                            id="address"
                                            name="address"
                                            className="form-input"
                                            placeholder="123 Medical Center Dr, Suite 100, City, State 12345"
                                            value={formData.address}
                                            onChange={handleInputChange}
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label htmlFor="phoneNumber" className="form-label">Phone Number</label>
                                        <input
                                            type="tel"
                                            id="phoneNumber"
                                            name="phoneNumber"
                                            className="form-input"
                                            placeholder="(555) 123-4567"
                                            value={formData.phoneNumber}
                                            onChange={handleInputChange}
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label htmlFor="licenseNumber" className="form-label">License Number</label>
                                        <input
                                            type="text"
                                            id="licenseNumber"
                                            name="licenseNumber"
                                            className="form-input"
                                            placeholder="MD123456"
                                            value={formData.licenseNumber}
                                            onChange={handleInputChange}
                                        />
                                    </div>

                                    <div className="form-group form-group--full">
                                        <label className="form-label">Affiliated Insurance Networks</label>
                                        <div className="insurance-grid">
                                            {INSURANCE_NETWORKS.map(network => (
                                                <label
                                                    key={network}
                                                    className={`insurance-chip ${formData.insuranceNetworks.includes(network) ? 'insurance-chip--selected' : ''}`}
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={formData.insuranceNetworks.includes(network)}
                                                        onChange={() => handleNetworkToggle(network)}
                                                    />
                                                    <span className="insurance-chip__check">✓</span>
                                                    <span>{network}</span>
                                                </label>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="form-group form-group--full">
                                        <label htmlFor="servicesOffered" className="form-label">Services Offered</label>
                                        <textarea
                                            id="servicesOffered"
                                            name="servicesOffered"
                                            className="form-textarea"
                                            placeholder="List the clinical services, procedures, or specializations offered by this provider..."
                                            rows={3}
                                            value={formData.servicesOffered}
                                            onChange={handleInputChange}
                                        />
                                    </div>

                                    {/* File Upload */}
                                    <div className="form-group form-group--full">
                                        <label className="form-label">Upload Documents</label>
                                        <p className="form-hint">Upload PDFs or images for additional verification (licenses, certifications, etc.)</p>

                                        <div
                                            className="file-upload"
                                            onClick={() => fileInputRef.current?.click()}
                                        >
                                            <input
                                                ref={fileInputRef}
                                                type="file"
                                                multiple
                                                accept=".pdf,image/*"
                                                onChange={handleFileUpload}
                                                className="file-upload__input"
                                            />
                                            <div className="file-upload__icon">
                                                <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                    <path d="M40 30V38C40 39.0609 39.5786 40.0783 38.8284 40.8284C38.0783 41.5786 37.0609 42 36 42H12C10.9391 42 9.92172 41.5786 9.17157 40.8284C8.42143 40.0783 8 39.0609 8 38V30" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                                                    <path d="M32 16L24 8L16 16" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                                                    <path d="M24 8V30" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                                                </svg>
                                            </div>
                                            <p className="file-upload__text">
                                                <span>Click to upload</span> or drag and drop
                                            </p>
                                            <p className="file-upload__hint">PDF, PNG, JPG up to 10MB each</p>
                                        </div>

                                        {uploadedFiles.length > 0 && (
                                            <div className="uploaded-files">
                                                {uploadedFiles.map((file, index) => (
                                                    <div key={index} className="uploaded-file">
                                                        <span className="uploaded-file__icon">
                                                            {file.type === 'application/pdf' ? '📄' : '🖼️'}
                                                        </span>
                                                        <span className="uploaded-file__name">{file.name}</span>
                                                        <span className="uploaded-file__size">
                                                            {(file.size / 1024).toFixed(1)} KB
                                                        </span>
                                                        <button
                                                            type="button"
                                                            className="uploaded-file__remove"
                                                            onClick={() => removeFile(index)}
                                                        >
                                                            ×
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            {/* Submit */}
                            <div className="verify-form__actions">
                                <button
                                    type="submit"
                                    className="btn btn--primary btn--lg"
                                    disabled={isSubmitting}
                                >
                                    {isSubmitting ? (
                                        <>
                                            <span className="btn-spinner"></span>
                                            Verifying...
                                        </>
                                    ) : (
                                        <>
                                            Verify Provider
                                            <svg viewBox="0 0 20 20" fill="currentColor">
                                                <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd" />
                                            </svg>
                                        </>
                                    )}
                                </button>
                                <Link to="/" className="btn btn--ghost btn--lg">
                                    Cancel
                                </Link>
                            </div>
                        </motion.form>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
};

export default VerifyPage;
