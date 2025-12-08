import { useState, useMemo, useRef, useCallback } from 'react';
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

// Field display names and icons
const FIELD_CONFIG = {
    fullName: { label: 'Full Name', icon: '👤', category: 'identity' },
    specialty: { label: 'Specialty', icon: '🏥', category: 'identity' },
    address: { label: 'Address', icon: '📍', category: 'contact' },
    phoneNumber: { label: 'Phone Number', icon: '📞', category: 'contact' },
    licenseNumber: { label: 'License Number', icon: '🪪', category: 'credentials' },
    insuranceNetworks: { label: 'Insurance Networks', icon: '🏛️', category: 'network' },
    servicesOffered: { label: 'Services Offered', icon: '⚕️', category: 'services' },
};

// Donut Chart Component
const DonutChart = ({ verified, unverified, notFound, missingDataFound }) => {
    const total = verified + unverified + notFound + (missingDataFound || 0);
    if (total === 0) return null;

    const verifiedPercent = (verified / total) * 100;
    const unverifiedPercent = (unverified / total) * 100;
    const notFoundPercent = (notFound / total) * 100;
    const missingDataPercent = ((missingDataFound || 0) / total) * 100;

    // Calculate stroke-dasharray for each segment
    const circumference = 2 * Math.PI * 45; // radius = 45
    const verifiedDash = (verifiedPercent / 100) * circumference;
    const unverifiedDash = (unverifiedPercent / 100) * circumference;
    const notFoundDash = (notFoundPercent / 100) * circumference;
    const missingDataDash = (missingDataPercent / 100) * circumference;

    return (
        <div className="donut-chart">
            <svg viewBox="0 0 120 120" className="donut-chart__svg">
                {/* Background circle */}
                <circle
                    cx="60"
                    cy="60"
                    r="45"
                    fill="none"
                    stroke="rgba(255,255,255,0.1)"
                    strokeWidth="12"
                />                {/* Not found segment */}
                <circle
                    cx="60"
                    cy="60"
                    r="45"
                    fill="none"
                    stroke="var(--neutral-500)"
                    strokeWidth="12"
                    strokeDasharray={`${notFoundDash} ${circumference}`}
                    strokeDashoffset={0}
                    transform="rotate(-90 60 60)"
                    className="donut-segment"
                />
                {/* Missing data found segment */}
                <circle
                    cx="60"
                    cy="60"
                    r="45"
                    fill="none"
                    stroke="var(--warning-400)"
                    strokeWidth="12"
                    strokeDasharray={`${missingDataDash} ${circumference}`}
                    strokeDashoffset={-notFoundDash}
                    transform="rotate(-90 60 60)"
                    className="donut-segment"
                />
                {/* Unverified segment */}
                <circle
                    cx="60"
                    cy="60"
                    r="45"
                    fill="none"
                    stroke="var(--error-400)"
                    strokeWidth="12"
                    strokeDasharray={`${unverifiedDash} ${circumference}`}
                    strokeDashoffset={-(notFoundDash + missingDataDash)}
                    transform="rotate(-90 60 60)"
                    className="donut-segment"
                />
                {/* Verified segment */}
                <circle
                    cx="60"
                    cy="60"
                    r="45"
                    fill="none"
                    stroke="var(--success-400)"
                    strokeWidth="12"
                    strokeDasharray={`${verifiedDash} ${circumference}`}
                    strokeDashoffset={-(notFoundDash + missingDataDash + unverifiedDash)}
                    transform="rotate(-90 60 60)"
                    className="donut-segment"
                />
                {/* Center text */}
                <text x="60" y="55" textAnchor="middle" className="donut-chart__value">
                    {Math.round(verifiedPercent)}%
                </text>
                <text x="60" y="72" textAnchor="middle" className="donut-chart__label">
                    Verified
                </text>
            </svg>            <div className="donut-chart__legend">
                <div className="donut-legend__item">
                    <span className="donut-legend__dot donut-legend__dot--verified"></span>
                    <span>Verified ({verified})</span>
                </div>
                <div className="donut-legend__item">
                    <span className="donut-legend__dot donut-legend__dot--unverified"></span>
                    <span>Mismatch ({unverified})</span>
                </div>
                {missingDataFound > 0 && (
                    <div className="donut-legend__item">
                        <span className="donut-legend__dot donut-legend__dot--missing-data"></span>
                        <span>Missing Data Found ({missingDataFound})</span>
                    </div>
                )}
                <div className="donut-legend__item">
                    <span className="donut-legend__dot donut-legend__dot--notfound"></span>
                    <span>Not Found ({notFound})</span>
                </div>
            </div>
        </div>
    );
};

// Bar Chart Component for field confidence
const FieldConfidenceChart = ({ fields }) => {
    return (
        <div className="field-chart">
            <h4 className="field-chart__title">Field Verification Status</h4>
            <div className="field-chart__bars">
                {fields.map((field, index) => (
                    <motion.div
                        key={field.name}
                        className="field-bar"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                    >
                        <div className="field-bar__info">
                            <span className="field-bar__icon">{field.icon}</span>
                            <span className="field-bar__name">{field.label}</span>
                        </div>                        <div className="field-bar__track">
                            <motion.div
                                className={`field-bar__fill field-bar__fill--${field.status}`}
                                initial={{ width: 0 }}
                                animate={{ 
                                    width: field.status === 'verified' ? '100%' : 
                                           field.status === 'mismatch' ? '100%' : 
                                           field.status === 'missing-data-found' ? '75%' : '30%' 
                                }}
                                transition={{ duration: 0.6, delay: 0.3 + index * 0.1 }}
                            />
                        </div>
                        <span className={`field-bar__status field-bar__status--${field.status}`}>
                            {field.status === 'verified' ? '✓' : 
                             field.status === 'mismatch' ? '✗' : 
                             field.status === 'missing-data-found' ? '📋' : '?'}
                        </span>
                    </motion.div>
                ))}
            </div>
        </div>
    );
};

// Source Distribution Component
const SourceDistribution = ({ sources }) => {
    const sourceCounts = {};
    sources.forEach(s => {
        if (s) {
            sourceCounts[s] = (sourceCounts[s] || 0) + 1;
        }
    });

    const sourceEntries = Object.entries(sourceCounts);
    const maxCount = Math.max(...Object.values(sourceCounts), 1);

    return (
        <div className="source-dist">
            <h4 className="source-dist__title">Data Sources</h4>
            <div className="source-dist__items">
                {sourceEntries.map(([source, count], index) => (
                    <motion.div
                        key={source}
                        className="source-item"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: index * 0.1 }}
                    >
                        <div className="source-item__header">
                            <span className="source-item__icon">
                                {source.includes('NPI') ? '🏛️' : source.includes('Google') ? '🌐' : '📊'}
                            </span>
                            <span className="source-item__name">{source}</span>
                        </div>
                        <div className="source-item__bar">
                            <motion.div
                                className="source-item__fill"
                                initial={{ width: 0 }}
                                animate={{ width: `${(count / maxCount) * 100}%` }}
                                transition={{ duration: 0.5, delay: 0.2 }}
                            />
                        </div>
                        <span className="source-item__count">{count} fields</span>
                    </motion.div>
                ))}
            </div>
        </div>
    );
};

// Verification Timeline Component
const VerificationTimeline = ({ timestamp, verificationId }) => {
    const steps = [
        { icon: '📥', label: 'Data Received', status: 'complete' },
        { icon: '🔍', label: 'Validation Started', status: 'complete' },
        { icon: '🌐', label: 'Sources Queried', status: 'complete' },
        { icon: '✅', label: 'Analysis Complete', status: 'complete' },
    ];

    return (
        <div className="timeline">
            <h4 className="timeline__title">Verification Process</h4>
            <div className="timeline__steps">
                {steps.map((step, index) => (
                    <motion.div
                        key={index}
                        className="timeline-step"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.15 }}
                    >
                        <div className="timeline-step__icon">{step.icon}</div>
                        <div className="timeline-step__content">
                            <span className="timeline-step__label">{step.label}</span>
                            {index === steps.length - 1 && (
                                <span className="timeline-step__time">
                                    {new Date(timestamp).toLocaleTimeString()}
                                </span>
                            )}
                        </div>
                        {index < steps.length - 1 && <div className="timeline-step__line" />}
                    </motion.div>
                ))}
            </div>
        </div>
    );
};

const VerifyPage = () => {
    const [activeTab, setActiveTab] = useState('form'); // 'form' or 'pdf'
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitResult, setSubmitResult] = useState(null);
    const [pdfFile, setPdfFile] = useState(null);
    const [pdfText, setPdfText] = useState('');
    const [isProcessingPdf, setIsProcessingPdf] = useState(false);
    const [pdfVerificationResult, setPdfVerificationResult] = useState(null);
    const [notification, setNotification] = useState(null);
    const fileInputRef = useRef(null);

    const [formData, setFormData] = useState({
        fullName: '',
        specialty: '',
        address: '',
        phoneNumber: '',
        licenseNumber: '',
        insuranceNetworks: [],
        servicesOffered: '',
    });

    const [errors, setErrors] = useState({});

    // Notification function
    const showNotification = useCallback((message, type = 'error') => {
        setNotification({ message, type });
        setTimeout(() => setNotification(null), 5000);
    }, []);

    // Calculate stats from results
    const resultStats = useMemo(() => {
        if (!submitResult?.success || !submitResult?.data) return null;

        const data = submitResult.data;
        const fieldKeys = ['fullName', 'specialty', 'address', 'phoneNumber', 'licenseNumber', 'insuranceNetworks', 'servicesOffered'];

        let verified = 0;
        let unverified = 0;
        let notFound = 0;
        let missingDataFound = 0;
        const fields = [];
        const sources = [];

        fieldKeys.forEach(key => {
            const field = data[key];
            if (field) {
                // Case 1: Verified - input provided + matches = true
                if (field.input_field_a && field.matches === true) {
                    verified++;
                    fields.push({ name: key, ...FIELD_CONFIG[key], status: 'verified' });
                }
                // Case 2: Unverified/Mismatch - input provided + matches = false
                else if (field.input_field_a && field.matches === false) {
                    unverified++;
                    fields.push({ name: key, ...FIELD_CONFIG[key], status: 'mismatch' });
                }
                // Case 3: Missing Data Found - input = null + matches = null + scraped_data available
                else if (!field.input_field_a && field.matches === null && field.scraped_data_field_a) {
                    missingDataFound++;
                    fields.push({ name: key, ...FIELD_CONFIG[key], status: 'missing-data-found' });
                }
                // Case 4: Not Found - no scraped data available
                else if (!field.scraped_data_field_a) {
                    notFound++;
                    fields.push({ name: key, ...FIELD_CONFIG[key], status: 'notfound' });
                }
                
                if (field.scraped_from) {
                    sources.push(field.scraped_from);
                }
            }
        });

        const total = verified + unverified + notFound + missingDataFound;
        const confidence = total > 0 ? Math.round((verified / total) * 100) : 0;

        return { verified, unverified, notFound, missingDataFound, confidence, fields, sources, total };
    }, [submitResult]);

    // PDF Processing Functions
    const processPDFForVerification = useCallback(async (file) => {
        setIsProcessingPdf(true);
        try {
            const formData = new FormData();
            formData.append('file', file);

            const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
            const response = await fetch(`${backendUrl}/api/doctor/extract-pdf`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                
                // Handle structured error responses
                if (errorData.detail && typeof errorData.detail === 'object') {
                    const { error, message, details, extracted_info } = errorData.detail;
                    
                    // Create short, professional error messages
                    let shortMessage = '';
                    if (error === 'PDF validation failed') {
                        shortMessage = 'Unable to extract valid doctor information from PDF';
                    } else if (error === 'Empty PDF') {
                        shortMessage = 'PDF contains no readable text';
                    } else if (error === 'Insufficient content') {
                        shortMessage = 'PDF has insufficient information for processing';
                    } else {
                        shortMessage = 'PDF processing failed';
                    }
                    
                    // Show extracted info if available
                    if (extracted_info) {
                        setPdfVerificationResult({
                            success: false,
                            extractedInfo: extracted_info,
                            error: shortMessage
                        });
                    }
                    
                    throw new Error(shortMessage);
                } else {
                    throw new Error(errorData.detail || 'Failed to process PDF');
                }
            }

            const result = await response.json();
            setPdfText(result.extracted_text || '');
            
            // Set verification results if available
            if (result.has_verification && result.verification_results) {
                setPdfVerificationResult({
                    success: true,
                    data: result.verification_results,
                    extractedInfo: result.provider_info
                });
            } else {
                // Show extracted info if verification couldn't be performed
                setPdfVerificationResult({
                    success: false,
                    extractedInfo: result.provider_info,
                    error: "Could not perform verification - insufficient data extracted from PDF"
                });
            }
            
            return result;
        } catch (error) {
            console.error('Error processing PDF:', error);
            throw new Error('Failed to process PDF: ' + error.message);
        } finally {
            setIsProcessingPdf(false);
        }
    }, []);

    const handlePdfUpload = useCallback(async (file) => {
        try {
            // Clear previous results before processing new file
            setPdfFile(null);
            setPdfText('');
            setPdfVerificationResult(null);
            
            setPdfFile(file);
            await processPDFForVerification(file);
        } catch (error) {
            console.error('Error processing PDF:', error);
            showNotification('Error processing PDF: ' + error.message);
        }
    }, [processPDFForVerification, showNotification]);

    const handleFileSelect = useCallback((event) => {
        const file = event.target.files[0];
        if (file && file.type === 'application/pdf') {
            handlePdfUpload(file);
        } else {
            showNotification('Please select a valid PDF file', 'warning');
        }
    }, [handlePdfUpload]);

    const resetPdfUpload = useCallback(() => {
        setPdfFile(null);
        setPdfText('');
        setPdfVerificationResult(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    }, []);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
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

    const validateForm = () => {
        const newErrors = {};
        if (!formData.fullName.trim()) newErrors.fullName = 'Full name is required';
        if (!formData.specialty) newErrors.specialty = 'Specialty is required';
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!validateForm()) return;

        setIsSubmitting(true);
        setSubmitResult(null);

        try {
            const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

            const payload = {
                fullName: formData.fullName,
                specialty: formData.specialty,
                address: formData.address || null,
                phoneNumber: formData.phoneNumber || null,
                licenseNumber: formData.licenseNumber || null,
                insuranceNetworks: formData.insuranceNetworks.length > 0 ? formData.insuranceNetworks : null,
                servicesOffered: formData.servicesOffered || null,
            };

            const response = await fetch(`${backendUrl}/api/doctor/verify`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const result = await response.json();

            if (response.ok) {
                setSubmitResult({ success: true, data: result });
            } else {
                setSubmitResult({ success: false, error: result.message || result.detail || 'Verification failed' });
            }
        } catch (error) {
            console.error('Verification error:', error);
            setSubmitResult({ success: false, error: 'Unable to connect to the verification service. Please try again.' });
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
        setSubmitResult(null);
        setErrors({});
    };    // Render verification result field
    const renderResultField = (fieldName, fieldData) => {
        if (!fieldData) return null;

        const config = FIELD_CONFIG[fieldName];
        let status, statusText, statusIcon;
        
        // Determine verification state
        if (fieldData.input_field_a && fieldData.matches === true) {
            // Case 1: Verified - input provided + matches = true
            status = 'match';
            statusText = '✓ Verified';
            statusIcon = '✓';
        } else if (fieldData.input_field_a && fieldData.matches === false) {
            // Case 2: Unverified/Mismatch - input provided + matches = false
            status = 'mismatch';
            statusText = '✗ Mismatch';
            statusIcon = '✗';
        } else if (!fieldData.input_field_a && fieldData.matches === null && fieldData.scraped_data_field_a) {
            // Case 3: Missing Data Found - input = null + matches = null + scraped_data available
            status = 'missing-data';
            statusText = '📋 Data Found';
            statusIcon = '📋';
        } else {
            // Don't render fields with no relevant data
            return null;
        }

        const inputValue = fieldData.input_field_a 
            ? (Array.isArray(fieldData.input_field_a)
                ? fieldData.input_field_a.join(', ')
                : fieldData.input_field_a)
            : null;

        const scrapedValue = fieldData.scraped_data_field_a
            ? (Array.isArray(fieldData.scraped_data_field_a)
                ? fieldData.scraped_data_field_a.join(', ')
                : fieldData.scraped_data_field_a)
            : 'Not found in database';

        return (
            <motion.div
                key={fieldName}
                className={`result-field result-field--${status}`}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
            >
                <div className="result-field__header">
                    <span className="result-field__icon">{config.icon}</span>
                    <span className="result-field__label">{config.label}</span>
                    <span className={`result-field__status result-field__status--${status}`}>
                        {statusText}
                    </span>
                </div>
                <div className="result-field__comparison">
                    <div className="result-field__value result-field__value--input">
                        <span className="result-field__value-label">Your Input</span>
                        <span className="result-field__value-text">
                            {inputValue || (status === 'missing-data' ? 'Not provided' : 'Not provided')}
                        </span>
                    </div>
                    <div className="result-field__arrow">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M5 12h14M12 5l7 7-7 7" />
                        </svg>
                    </div>
                    <div className="result-field__value result-field__value--scraped">
                        <span className="result-field__value-label">
                            {fieldData.scraped_from ? `From ${fieldData.scraped_from}` : 'Verified Data'}
                        </span>
                        <span className="result-field__value-text">{scrapedValue}</span>
                    </div>
                </div>
                {status === 'missing-data' && (
                    <div className="result-field__note">
                        <span className="result-field__note-icon">💡</span>
                        <span className="result-field__note-text">
                            This information was not provided but was found in our verification sources.
                        </span>
                    </div>
                )}
            </motion.div>
        );
    };

    return (
        <div className="verify-page">
            {/* Notification Popup */}
            {notification && (
                <motion.div
                    className={`notification notification--${notification.type}`}
                    initial={{ opacity: 0, y: -50, scale: 0.9 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -50, scale: 0.9 }}
                    transition={{ duration: 0.3 }}
                >
                    <div className="notification__icon">
                        {notification.type === 'error' ? '❌' : 
                         notification.type === 'warning' ? '⚠️' : 
                         notification.type === 'success' ? '✅' : 'ℹ️'}
                    </div>
                    <div className="notification__content">
                        <p className="notification__message">{notification.message}</p>
                    </div>
                    <button
                        className="notification__close"
                        onClick={() => setNotification(null)}
                    >
                        ×
                    </button>
                </motion.div>
            )}
            
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
                    {submitResult?.success ? (
                        <motion.div
                            key="result"
                            className="verification-results"
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            transition={{ duration: 0.4 }}
                        >
                            {/* Results Window */}
                            <div className="results-window">
                                <div className="results-window__header">
                                    <div className="results-window__dots">
                                        <span></span><span></span><span></span>
                                    </div>
                                    <span>Provider Validation Results</span>
                                    <span className="results-window__id">{submitResult.data.verification_id}</span>
                                </div>

                                <div className="results-window__content">
                                    {/* Provider Summary */}
                                    <div className="provider-summary">
                                        <div className="provider-summary__avatar">👨‍⚕️</div>
                                        <div className="provider-summary__info">
                                            <h2 className="provider-summary__name">
                                                {submitResult.data.fullName?.input_field_a || formData.fullName}
                                            </h2>
                                            <p className="provider-summary__specialty">
                                                {submitResult.data.specialty?.input_field_a || formData.specialty}
                                            </p>
                                        </div>
                                        <div className={`provider-summary__badge ${resultStats?.confidence >= 70 ? 'provider-summary__badge--verified' : 'provider-summary__badge--warning'}`}>
                                            {resultStats?.confidence >= 70 ? '✓ Verified' : '⚠ Review Needed'}
                                        </div>
                                    </div>

                                    {/* Dashboard Stats Grid */}
                                    <div className="stats-dashboard">                                        {/* Donut Chart */}
                                        <div className="stats-card stats-card--chart">
                                            <DonutChart
                                                verified={resultStats?.verified || 0}
                                                unverified={resultStats?.unverified || 0}
                                                notFound={resultStats?.notFound || 0}
                                                missingDataFound={resultStats?.missingDataFound || 0}
                                            />
                                        </div>

                                        {/* Quick Stats */}
                                        <div className="stats-card stats-card--numbers">
                                            <h4 className="stats-card__title">Verification Summary</h4>                                            <div className="stats-numbers">
                                                <div className="stat-number stat-number--verified">
                                                    <span className="stat-number__value">{resultStats?.verified || 0}</span>
                                                    <span className="stat-number__label">Verified</span>
                                                </div>
                                                <div className="stat-number stat-number--mismatch">
                                                    <span className="stat-number__value">{resultStats?.unverified || 0}</span>
                                                    <span className="stat-number__label">Mismatched</span>
                                                </div>
                                                {(resultStats?.missingDataFound || 0) > 0 && (
                                                    <div className="stat-number stat-number--missing-data">
                                                        <span className="stat-number__value">{resultStats?.missingDataFound || 0}</span>
                                                        <span className="stat-number__label">Data Found</span>
                                                    </div>
                                                )}
                                                <div className="stat-number stat-number--notfound">
                                                    <span className="stat-number__value">{resultStats?.notFound || 0}</span>
                                                    <span className="stat-number__label">Not Found</span>
                                                </div>
                                                <div className="stat-number stat-number--total">
                                                    <span className="stat-number__value">{resultStats?.total || 0}</span>
                                                    <span className="stat-number__label">Total Fields</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Field Confidence Chart */}
                                    <div className="chart-section">
                                        {resultStats?.fields && <FieldConfidenceChart fields={resultStats.fields} />}
                                    </div>

                                    {/* Source Distribution & Timeline */}
                                    <div className="insights-grid">
                                        {resultStats?.sources?.length > 0 && (
                                            <SourceDistribution sources={resultStats.sources} />
                                        )}
                                        <VerificationTimeline
                                            timestamp={submitResult.data.timestamp}
                                            verificationId={submitResult.data.verification_id}
                                        />
                                    </div>

                                    {/* Detailed Results */}
                                    <div className="results-grid">
                                        <h3 className="results-grid__title">
                                            <span className="results-grid__title-icon">📋</span>
                                            Detailed Field Comparison
                                        </h3>
                                        <div className="results-grid__fields">
                                            {renderResultField('fullName', submitResult.data.fullName)}
                                            {renderResultField('specialty', submitResult.data.specialty)}
                                            {renderResultField('address', submitResult.data.address)}
                                            {renderResultField('phoneNumber', submitResult.data.phoneNumber)}
                                            {renderResultField('licenseNumber', submitResult.data.licenseNumber)}
                                            {renderResultField('insuranceNetworks', submitResult.data.insuranceNetworks)}
                                            {renderResultField('servicesOffered', submitResult.data.servicesOffered)}
                                        </div>
                                    </div>

                                    {/* Confidence Meter */}
                                    <div className="confidence-section">
                                        <div className="confidence-header">
                                            <span className="confidence-label">Overall Confidence Score</span>
                                            <span className={`confidence-value ${resultStats?.confidence >= 70 ? 'confidence-value--high' : resultStats?.confidence >= 40 ? 'confidence-value--medium' : 'confidence-value--low'}`}>
                                                {resultStats?.confidence || 0}%
                                            </span>
                                        </div>
                                        <div className="confidence-bar">
                                            <motion.div
                                                className={`confidence-fill ${resultStats?.confidence >= 70 ? 'confidence-fill--high' : resultStats?.confidence >= 40 ? 'confidence-fill--medium' : 'confidence-fill--low'}`}
                                                initial={{ width: 0 }}
                                                animate={{ width: `${resultStats?.confidence || 0}%` }}
                                                transition={{ duration: 1, delay: 0.3, ease: 'easeOut' }}
                                            />
                                            <div className="confidence-markers">
                                                <span className="confidence-marker" style={{ left: '33%' }}>Low</span>
                                                <span className="confidence-marker" style={{ left: '66%' }}>Medium</span>
                                                <span className="confidence-marker" style={{ left: '100%' }}>High</span>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Timestamp */}
                                    <div className="results-timestamp">
                                        <span className="results-timestamp__icon">🕐</span>
                                        Verified on {new Date(submitResult.data.timestamp).toLocaleString()}
                                    </div>
                                </div>
                            </div>

                            {/* Actions */}
                            <div className="results-actions">
                                <button onClick={resetForm} className="btn btn--primary btn--lg">
                                    <span>🔄</span> Verify Another Provider
                                </button>
                                <Link to="/" className="btn btn--ghost btn--lg">
                                    <span>🏠</span> Back to Home
                                </Link>
                            </div>
                        </motion.div>
                    ) : submitResult?.success === false ? (
                        <motion.div
                            key="error"
                            className="verify-page__result"
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            transition={{ duration: 0.3 }}
                        >
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
                        </motion.div>
                    ) : (
                        <motion.div
                            key="form"
                            className="verify-form-container"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            transition={{ duration: 0.4 }}
                        >
                            {/* Tab Navigation */}
                            <div className="verify-tabs">
                                <button
                                    className={`verify-tab ${activeTab === 'form' ? 'verify-tab--active' : ''}`}
                                    onClick={() => setActiveTab('form')}
                                >
                                    <span className="verify-tab__icon">📝</span>
                                    Form Validation
                                </button>
                                <button
                                    className={`verify-tab ${activeTab === 'pdf' ? 'verify-tab--active' : ''}`}
                                    onClick={() => setActiveTab('pdf')}
                                >
                                    <span className="verify-tab__icon">📄</span>
                                    PDF Upload
                                </button>
                            </div>

                            {/* Tab Content */}
                            <AnimatePresence mode="wait">
                                {activeTab === 'form' ? (
                                    <motion.form
                                        key="form-tab"
                                        className="verify-form"
                                        onSubmit={handleSubmit}
                                        initial={{ opacity: 0, x: 20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: -20 }}
                                        transition={{ duration: 0.3 }}
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
                                                        placeholder="Dr. Sarah Johnson, MD"
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
                                                        placeholder="List the clinical services, procedures, or specializations..."
                                                        rows={3}
                                                        value={formData.servicesOffered}
                                                        onChange={handleInputChange}
                                                    />
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
                                ) : (
                                    <motion.div
                                        key="pdf-tab"
                                        className="pdf-upload-section"
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        exit={{ opacity: 0, x: 20 }}
                                        transition={{ duration: 0.3 }}
                                    >
                                        <div className="pdf-upload">
                                            <div className="pdf-upload__header">
                                                <h2 className="pdf-upload__title">Upload Provider Document</h2>
                                                <p className="pdf-upload__subtitle">
                                                    Upload a PDF document containing provider information for automatic extraction
                                                </p>
                                            </div>

                                            <div className="pdf-upload__dropzone">
                                                <input
                                                    type="file"
                                                    accept=".pdf"
                                                    onChange={handleFileSelect}
                                                    ref={fileInputRef}
                                                    className="pdf-upload__input"
                                                />
                                                
                                                <div className="pdf-upload__content">
                                                    {isProcessingPdf ? (
                                                        <div className="pdf-upload__processing">
                                                            <div className="pdf-upload__spinner"></div>
                                                            <p>Processing PDF...</p>
                                                        </div>
                                                    ) : pdfFile ? (
                                                        <div className="pdf-upload__success">
                                                            <div className="pdf-upload__icon">✓</div>
                                                            <h3>{pdfFile.name}</h3>
                                                            <p>File uploaded successfully</p>
                                                            <button
                                                                onClick={resetPdfUpload}
                                                                className="btn btn--ghost btn--sm"
                                                            >
                                                                Upload Different File
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <div className="pdf-upload__placeholder">
                                                            <div className="pdf-upload__icon">📄</div>
                                                            <h3>Drop your PDF here</h3>
                                                            <p>or click to browse files</p>
                                                            <button
                                                                type="button"
                                                                onClick={() => fileInputRef.current?.click()}
                                                                className="btn btn--primary"
                                                            >
                                                                Select PDF File
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>

                                            {/* PDF Verification Results - Only show container if successful */}
                                            {pdfVerificationResult && pdfVerificationResult.success && (
                                                <motion.div
                                                    className="pdf-verification-results"
                                                    initial={{ opacity: 0, y: 20 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    transition={{ duration: 0.4 }}
                                                >
                                                    <div className="pdf-verification-success">
                                                        <h3 className="pdf-verification-title">
                                                            <span className="pdf-verification-icon">✅</span>
                                                            PDF Verification Complete
                                                        </h3>
                                                        
                                                        <div className="pdf-verification-summary">
                                                            <p>Provider information was extracted and verified against our database.</p>
                                                            <button
                                                                onClick={() => setSubmitResult(pdfVerificationResult)}
                                                                className="btn btn--primary btn--lg"
                                                            >
                                                                <span>📊</span>
                                                                View Detailed Results
                                                            </button>
                                                        </div>
                                                    </div>
                                                </motion.div>
                                            )}

                                            {/* PDF Error Action Buttons - Show directly when PDF processing fails */}
                                            {pdfVerificationResult && !pdfVerificationResult.success && (
                                                <motion.div
                                                    className="pdf-error-actions"
                                                    initial={{ opacity: 0, y: 20 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    transition={{ duration: 0.4, delay: 0.1 }}
                                                >
                                                    <button
                                                        onClick={resetPdfUpload}
                                                        className="btn btn--ghost btn--lg pdf-action-btn"
                                                    >
                                                        <span className="btn-icon">📄</span>
                                                        <span>Try Another PDF</span>
                                                    </button>
                                                    <button
                                                        onClick={() => setActiveTab('form')}
                                                        className="btn btn--primary btn--lg pdf-action-btn"
                                                    >
                                                        <span className="btn-icon">📝</span>
                                                        <span>Use Form Instead</span>
                                                    </button>
                                                </motion.div>
                                            )}
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
};

export default VerifyPage;
