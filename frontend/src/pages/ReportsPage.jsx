import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import * as XLSX from 'xlsx';
import './ReportsPage.css';
import './VerifyPage.css'; // Import VerifyPage CSS for statistical components

// Field display names and icons (same as VerifyPage)
const FIELD_CONFIG = {
    fullName: { label: 'Full Name', icon: '👤', category: 'identity' },
    specialty: { label: 'Specialty', icon: '🏥', category: 'identity' },
    address: { label: 'Address', icon: '📍', category: 'contact' },
    phoneNumber: { label: 'Phone Number', icon: '📞', category: 'contact' },
    licenseNumber: { label: 'License Number', icon: '🪪', category: 'credentials' },
    insuranceNetworks: { label: 'Insurance Networks', icon: '🏛️', category: 'network' },
    servicesOffered: { label: 'Services Offered', icon: '⚕️', category: 'services' },
};

// Donut Chart Component (exact same as VerifyPage)
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
                />
                {/* Not found segment */}
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
                {/* Mismatch segment */}
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
            </svg>
            <div className="donut-chart__legend">
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

// Bar Chart Component for field confidence (exact same as VerifyPage)
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
                        </div>
                        <div className="field-bar__track">
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

// Source Distribution Component (exact same as VerifyPage)
const SourceDistribution = ({ sources }) => {
    const sourceCounts = {};
    sources.forEach(s => {
        sourceCounts[s] = (sourceCounts[s] || 0) + 1;
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

// Verification Timeline Component (exact same as VerifyPage)
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

const SPECIALTIES = [
    'All',
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
    'Vascular Surgery'
];

const ReportsPage = () => {
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedSpecialty, setSelectedSpecialty] = useState('All');
    const [currentPage, setCurrentPage] = useState(1);
    const [reportsPerPage, setReportsPerPage] = useState(10);
    const [totalCount, setTotalCount] = useState(0);
    const [sortField, setSortField] = useState('created_at');
    const [sortOrder, setSortOrder] = useState('descend');
    const [submitResult, setSubmitResult] = useState(null);
    const [showDetailModal, setShowDetailModal] = useState(false);
    const [selectedReport, setSelectedReport] = useState(null);
    const [isVerifyingAll, setIsVerifyingAll] = useState(false);
    const [verifyAllResult, setVerifyAllResult] = useState(null);
    const [isExpanded, setIsExpanded] = useState(false);

    // Fetch reports from API
    const fetchReports = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams({
                skip: ((currentPage - 1) * reportsPerPage).toString(),
                limit: reportsPerPage.toString(),
                sort_field: sortField,
                sort_order: sortOrder
            });

            if (searchTerm.trim()) {
                params.append('full_name', searchTerm.trim());
            }

            if (selectedSpecialty !== 'All') {
                params.append('specialty', selectedSpecialty);
            }

            const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
            const response = await fetch(`${backendUrl}/api/doctor/reports?${params}`);
            const data = await response.json();

            if (response.ok) {
                setReports(data.reports);
                setTotalCount(data.total_count);
            } else {
                console.error('Failed to fetch reports:', data.detail);
                setReports([]);
                setTotalCount(0);
            }
        } catch (error) {
            console.error('Error fetching reports:', error);
            setReports([]);
            setTotalCount(0);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchReports();
    }, [currentPage, reportsPerPage, searchTerm, selectedSpecialty, sortField, sortOrder]);

    // Reset to first page when filters change
    useEffect(() => {
        if (currentPage !== 1) {
            setCurrentPage(1);
        }
    }, [searchTerm, selectedSpecialty]);

    const handleSearchChange = (e) => {
        setSearchTerm(e.target.value);
    };

    const handleSpecialtyChange = (specialty) => {
        setSelectedSpecialty(specialty);
    };

    const handleResetFilters = () => {
        setSearchTerm('');
        setSelectedSpecialty('All');
        setCurrentPage(1);
    };

    // Handle verify all doctors
    const handleVerifyAll = async () => {
        setIsVerifyingAll(true);
        setVerifyAllResult(null);
        try {
            const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
            const response = await fetch(`${backendUrl}/api/doctor/verify-all`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const result = await response.json();
            if (response.ok) {
                setVerifyAllResult({ success: true, data: result });
                fetchReports();
            } else {
                setVerifyAllResult({ success: false, error: result.detail || 'Verification failed' });
            }
        } catch (error) {
            console.error('Error running verify all:', error);
            setVerifyAllResult({ success: false, error: 'Failed to connect to server' });
        } finally {
            setIsVerifyingAll(false);
        }
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    };

    const getDisplayName = (report) => {
        return report.full_name_input || report.full_name_scraped || 'N/A';
    };

    const getDisplaySpecialty = (report) => {
        return report.specialty_input || report.specialty_scraped || 'N/A';
    };

    const totalPages = Math.ceil(totalCount / reportsPerPage);

    const handleViewReport = (report) => {
        setSelectedReport(report);
        setIsExpanded(false);
        setShowDetailModal(true);
    };

    // Download reports as Excel with styling
    const handleDownloadExcel = () => {
        if (reports.length === 0) return;

        // Prepare data for Excel with styling info
        const excelData = reports.map(report => {
            const stats = calculateVerificationStats(report);
            const needsAttention = stats.confidence < 70 || stats.unverified > 0;
            return {
                data: {
                    'Verification ID': report.verification_id || 'N/A',
                    'Provider Name': report.full_name_input || report.full_name_scraped || 'N/A',
                    'Specialty': report.specialty_input || report.specialty_scraped || 'N/A',
                    'Address (Input)': report.address_input || 'N/A',
                    'Address (Found)': report.address_scraped || 'N/A',
                    'Phone (Input)': report.phone_number_input || 'N/A',
                    'Phone (Found)': report.phone_number_scraped || 'N/A',
                    'License (Input)': report.license_number_input || 'N/A',
                    'License (Found)': report.license_number_scraped || 'N/A',
                    'Verified': stats.verified,
                    'Mismatched': stats.unverified,
                    'Not Found': stats.notFound,
                    'Confidence': stats.confidence,
                    'Status': stats.confidence >= 70 ? 'Verified' : stats.unverified > 0 ? 'Needs Review' : 'Incomplete',
                    'Date': report.created_at ? new Date(report.created_at).toLocaleDateString() : 'N/A'
                },
                needsAttention,
                confidence: stats.confidence,
                mismatches: stats.unverified
            };
        });

        // Generate styled HTML table for Excel
        const html = generateStyledExcelHtml(excelData);
        const blob = new Blob([html], { type: 'application/vnd.ms-excel' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const date = new Date().toISOString().split('T')[0];
        link.download = `Provider_Verification_Reports_${date}.xls`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    // Generate styled HTML for Excel export
    const generateStyledExcelHtml = (data) => {
        const headers = Object.keys(data[0]?.data || {});

        let html = `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel">
        <head><meta charset="UTF-8">
        <style>
            table { border-collapse: collapse; font-family: Calibri, Arial; font-size: 11pt; }
            th { background-color: #1a2332; color: #ffffff; font-weight: bold; padding: 10px 8px; border: 1px solid #0d1421; text-align: center; }
            td { padding: 8px; border: 1px solid #dee2e6; }
            .attention { background-color: #ffebee !important; }
            .attention td { background-color: #ffebee; }
            .good { background-color: #e8f5e9; }
            .good td { background-color: #e8f5e9; }
        </style></head><body><table>
        <tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr>`;

        data.forEach(row => {
            const cls = row.needsAttention ? 'attention' : (row.confidence >= 70 ? 'good' : '');

            html += `<tr class="${cls}">`;
            headers.forEach(h => {
                let style = '';
                let val = row.data[h];

                if (h === 'Confidence') {
                    style = row.confidence >= 70 ? 'color:#1b5e20;font-weight:bold' : 'color:#b71c1c;font-weight:bold';
                    val = val + '%';
                } else if (h === 'Status') {
                    if (val === 'Verified') style = 'color:#1b5e20;font-weight:bold;background-color:#c8e6c9';
                    else if (val === 'Needs Review') style = 'color:#b71c1c;font-weight:bold;background-color:#ffcdd2';
                    else style = 'color:#e65100;font-weight:bold;background-color:#fff3e0';
                } else if (h === 'Mismatched' && row.mismatches > 0) {
                    style = 'color:#b71c1c;font-weight:bold';
                } else if (h === 'Provider Name') {
                    style = 'font-weight:bold';
                } else if (h === 'Verified') {
                    style = 'color:#1b5e20;font-weight:bold';
                }

                html += `<td style="${style}">${val}</td>`;
            });
            html += '</tr>';
        });

        html += '</table></body></html>';
        return html;
    };

    const calculateVerificationStats = (report) => {
        if (!report) return {
            verified: 0,
            unverified: 0,
            notFound: 0,
            missingDataFound: 0,
            totalFields: 0,
            confidence: 0,
            fields: [],
            sources: []
        };

        // Map field names to their database column prefixes
        const fieldMapping = {
            fullName: { prefix: 'full_name', label: 'Full Name', icon: '👤' },
            specialty: { prefix: 'specialty', label: 'Specialty', icon: '🏥' },
            address: { prefix: 'address', label: 'Address', icon: '📍' },
            phoneNumber: { prefix: 'phone_number', label: 'Phone Number', icon: '📞' },
            licenseNumber: { prefix: 'license_number', label: 'License Number', icon: '🪪' },
            insuranceNetworks: { prefix: 'insurance_networks', label: 'Insurance Networks', icon: '🏛️' },
            servicesOffered: { prefix: 'services_offered', label: 'Services Offered', icon: '⚕️' },
        };

        let verified = 0;
        let unverified = 0;
        let notFound = 0;
        let missingDataFound = 0;
        const fields = [];
        const sources = [];

        Object.entries(fieldMapping).forEach(([fieldName, config]) => {
            const inputValue = report[config.prefix + '_input'];
            const scrapedValue = report[config.prefix + '_scraped'];
            const matches = report[config.prefix + '_matches'];
            const source = report[config.prefix + '_scraped_from'];

            let status = 'notfound';

            if (matches === true) {
                verified++;
                status = 'verified';
            } else if (matches === false) {
                unverified++;
                status = 'mismatch';
            } else if (!inputValue && scrapedValue) {
                missingDataFound++;
                status = 'missing-data-found';
            } else {
                notFound++;
            }

            if (source) {
                sources.push(source);
            }

            fields.push({
                name: fieldName,
                label: config.label,
                icon: config.icon,
                status
            });
        });

        const totalFields = Object.keys(fieldMapping).length;
        const confidence = Math.round((verified / totalFields) * 100);

        return {
            verified,
            unverified,
            notFound,
            missingDataFound,
            totalFields,
            confidence,
            fields,
            sources
        };
    };

    // Convert report data to match VerifyPage format
    const convertReportToVerifyFormat = (report) => {
        return {
            verification_id: report.verification_id,
            timestamp: report.created_at,
            fullName: {
                input_field_a: report.full_name_input,
                scraped_data_field_a: report.full_name_scraped,
                scraped_from: report.full_name_scraped_from,
                matches: report.full_name_matches
            },
            specialty: {
                input_field_a: report.specialty_input,
                scraped_data_field_a: report.specialty_scraped,
                scraped_from: report.specialty_scraped_from,
                matches: report.specialty_matches
            },
            address: {
                input_field_a: report.address_input,
                scraped_data_field_a: report.address_scraped,
                scraped_from: report.address_scraped_from,
                matches: report.address_matches
            },
            phoneNumber: {
                input_field_a: report.phone_number_input,
                scraped_data_field_a: report.phone_number_scraped,
                scraped_from: report.phone_number_scraped_from,
                matches: report.phone_number_matches
            },
            licenseNumber: {
                input_field_a: report.license_number_input,
                scraped_data_field_a: report.license_number_scraped,
                scraped_from: report.license_number_scraped_from,
                matches: report.license_number_matches
            },
            insuranceNetworks: {
                input_field_a: report.insurance_networks_input,
                scraped_data_field_a: report.insurance_networks_scraped,
                scraped_from: report.insurance_networks_scraped_from,
                matches: report.insurance_networks_matches
            },
            servicesOffered: {
                input_field_a: report.services_offered_input,
                scraped_data_field_a: report.services_offered_scraped,
                scraped_from: report.services_offered_scraped_from,
                matches: report.services_offered_matches
            }
        };
    };

    // Render verification result field (same as VerifyPage)
    const renderResultField = (fieldName, fieldData) => {
        const fieldConfig = {
            fullName: { label: 'Full Name', icon: '👤' },
            specialty: { label: 'Specialty', icon: '🏥' },
            address: { label: 'Address', icon: '📍' },
            phoneNumber: { label: 'Phone Number', icon: '📞' },
            licenseNumber: { label: 'License Number', icon: '🪪' },
            insuranceNetworks: { label: 'Insurance Networks', icon: '🏛️' },
            servicesOffered: { label: 'Services Offered', icon: '⚕️' },
        };

        if (!fieldData) return null;

        const config = fieldConfig[fieldName];
        const status = fieldData.matches === true ? 'verified' :
            fieldData.matches === false ? 'mismatch' : 'not-found';

        const inputValue = fieldData.input_field_a;
        const scrapedValue = fieldData.scraped_data_field_a;
        const source = fieldData.scraped_from;

        return (
            <motion.div
                key={fieldName}
                className={`result-field result-field--${status}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
            >
                <div className="result-field__header">
                    <div className="result-field__title">
                        <span className="result-field__icon">{config.icon}</span>
                        <span className="result-field__label">{config.label}</span>
                    </div>
                    <span className={`result-field__status result-field__status--${status}`}>
                        {status === 'verified' ? '✓ Verified' :
                            status === 'mismatch' ? '✗ Mismatch' : '? Not Found'}
                    </span>
                </div>
                <div className="result-field__content">
                    <div className="result-field__comparison">
                        <div className="result-field__value result-field__value--input">
                            <span className="result-field__value-label">Input:</span>
                            <span className="result-field__value-text">
                                {Array.isArray(inputValue) ? inputValue.join(', ') : inputValue || 'Not provided'}
                            </span>
                        </div>
                        <div className="result-field__value result-field__value--scraped">
                            <span className="result-field__value-label">Found:</span>
                            <span className="result-field__value-text">
                                {Array.isArray(scrapedValue) ? scrapedValue.join(', ') : scrapedValue || 'Not found'}
                            </span>
                            {source && (
                                <span className="result-field__source">via {source}</span>
                            )}
                        </div>
                    </div>
                </div>
            </motion.div>
        );
    };

    return (
        <div className="reports-page">
            {/* Header */}
            <div className="reports-header">
                <motion.div
                    className="reports-header-content"
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                >
                    <div className="reports-title-section">
                        <h1 className="reports-title">Provider Verified Reports</h1>
                        <p className="reports-subtitle">
                            Manage and audit the verification status of healthcare providers. View detailed reports,
                            specialty classifications, and verification timestamps.
                        </p>
                    </div>
                    <motion.button
                        className="verify-all-button"
                        onClick={handleVerifyAll}
                        disabled={isVerifyingAll}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                    >
                        {isVerifyingAll ? (
                            <><div className="verify-all-button__spinner" />Verifying...</>
                        ) : (
                            <><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>Run Verify All</>
                        )}
                    </motion.button>
                    <motion.button
                        className="download-excel-button"
                        onClick={handleDownloadExcel}
                        disabled={reports.length === 0}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                    >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Download Excel
                    </motion.button>
                </motion.div>
            </div>

            {/* Verify All Result Notification */}
            {verifyAllResult && (
                <motion.div
                    className={`verify-all-notification ${verifyAllResult.success ? 'verify-all-notification--success' : 'verify-all-notification--error'}`}
                    initial={{ opacity: 0, y: -30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3 }}
                >
                    <div className="verify-all-notification__content">
                        {verifyAllResult.success ? (
                            <p>✅ Bulk verification complete: {verifyAllResult.data.successful} successful, {verifyAllResult.data.failed} failed, {verifyAllResult.data.skipped} skipped</p>
                        ) : (
                            <p>❌ {verifyAllResult.error}</p>
                        )}
                    </div>
                    <button className="verify-all-notification__close" onClick={() => setVerifyAllResult(null)}>×</button>
                </motion.div>
            )}

            {/* Filters */}
            <div className="reports-filters">
                <motion.div
                    className="search-container"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                >
                    <div className="search-input-wrapper">
                        <svg className="search-icon" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
                        </svg>
                        <input
                            type="text"
                            placeholder="Search by provider name..."
                            value={searchTerm}
                            onChange={handleSearchChange}
                            className="search-input"
                        />
                    </div>
                </motion.div>

                <motion.div
                    className="specialty-filter"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                >
                    <select
                        value={selectedSpecialty}
                        onChange={(e) => handleSpecialtyChange(e.target.value)}
                        className="specialty-select"
                    >
                        <option value="All">Select Speciality</option>
                        {SPECIALTIES.slice(1).map((specialty) => (
                            <option key={specialty} value={specialty}>
                                {specialty}
                            </option>
                        ))}
                    </select>
                    <svg className="select-arrow" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                </motion.div>

                <motion.button
                    className="reset-button"
                    onClick={handleResetFilters}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.5, delay: 0.3 }}
                >
                    Reset
                </motion.button>
            </div>

            {/* Specialty Tags */}
            <motion.div
                className="specialty-tags"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.4 }}
            >
                {['All', 'Cardiology', 'Neurology', 'Pediatrics', 'Dermatology'].map((specialty) => (
                    <button
                        key={specialty}
                        className={`specialty-tag ${selectedSpecialty === specialty ? 'active' : ''}`}
                        onClick={() => handleSpecialtyChange(specialty)}
                    >
                        {specialty}
                    </button>
                ))}
            </motion.div>

            {/* Reports Grid */}
            <div className="reports-container">
                {loading ? (
                    <div className="loading-container">
                        <div className="loading-spinner"></div>
                        <p>Loading reports...</p>
                    </div>
                ) : reports.length === 0 ? (
                    <motion.div
                        className="no-reports"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.5 }}
                    >
                        <div className="no-reports-icon">
                            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <path d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                        </div>
                        <h3>No Reports Found</h3>
                        <p>Try adjusting your search criteria or filters</p>
                    </motion.div>
                ) : (
                    <motion.div
                        className="reports-grid"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.5, delay: 0.2 }}
                    >
                        <AnimatePresence>
                            {reports.map((report, index) => (
                                <motion.div
                                    key={report.report_id}
                                    className="report-card"
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -20 }}
                                    transition={{ duration: 0.3, delay: index * 0.1 }}
                                    whileHover={{ y: -5 }}
                                >
                                    <div className="report-card-header">
                                        <div className="doctor-avatar">
                                            <div className="avatar-icon">
                                                {getDisplayName(report).charAt(0).toUpperCase()}
                                            </div>
                                            <div className="verification-badge">
                                                <svg viewBox="0 0 20 20" fill="currentColor">
                                                    <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                </svg>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="report-card-content">
                                        <h3 className="doctor-name">{getDisplayName(report)}</h3>
                                        <p className="doctor-specialty">{getDisplaySpecialty(report)}</p>
                                        <div className="verification-date">
                                            <svg viewBox="0 0 20 20" fill="currentColor">
                                                <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                                            </svg>
                                            Verified: {formatDate(report.created_at)}
                                        </div>
                                    </div>

                                    <div className="report-card-footer">
                                        <motion.button
                                            className="view-report-button"
                                            whileHover={{ scale: 1.02 }}
                                            whileTap={{ scale: 0.98 }}
                                            onClick={() => handleViewReport(report)}
                                        >
                                            View Report
                                            <svg viewBox="0 0 20 20" fill="currentColor">
                                                <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                                            </svg>
                                        </motion.button>
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </motion.div>
                )}
            </div>

            {/* Pagination */}
            {totalCount > 0 && (
                <motion.div
                    className="pagination-container"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.3 }}
                >
                    <div className="pagination-info">
                        <div className="rows-per-page">
                            <label>Rows per page:</label>
                            <select
                                value={reportsPerPage}
                                onChange={(e) => {
                                    setReportsPerPage(Number(e.target.value));
                                    setCurrentPage(1);
                                }}
                                className="rows-select"
                            >
                                <option value={10}>10</option>
                                <option value={25}>25</option>
                                <option value={50}>50</option>
                            </select>
                        </div>
                        <div className="page-info">
                            {((currentPage - 1) * reportsPerPage) + 1}-{Math.min(currentPage * reportsPerPage, totalCount)} of {totalCount}
                        </div>
                    </div>

                    <div className="pagination-controls">
                        <button
                            className="pagination-button"
                            disabled={currentPage === 1}
                            onClick={() => setCurrentPage(currentPage - 1)}
                        >
                            <svg viewBox="0 0 20 20" fill="currentColor">
                                <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                        </button>
                        <button
                            className="pagination-button"
                            disabled={currentPage === totalPages}
                            onClick={() => setCurrentPage(currentPage + 1)}
                        >
                            <svg viewBox="0 0 20 20" fill="currentColor">
                                <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                            </svg>
                        </button>
                    </div>
                </motion.div>
            )}

            {/* Detailed Report Modal */}
            <AnimatePresence>
                {showDetailModal && selectedReport && (
                    <motion.div
                        className="verification-results-fullscreen"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        {(() => {
                            const convertedData = convertReportToVerifyFormat(selectedReport);
                            const resultStats = calculateVerificationStats(selectedReport);

                            return (
                                <motion.div
                                    className={`verification-results ${isExpanded ? 'verification-results--expanded' : 'verification-results--popup'}`}
                                    initial={{ opacity: 0, scale: 0.95 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.95 }}
                                    transition={{ duration: 0.4 }}
                                >
                                    {/* Results Window */}
                                    <div className="results-window">
                                        <div className="results-window__header">
                                            <div className="results-window__dots">
                                                <button 
                                                    className="window-dot window-dot--close"
                                                    onClick={() => setShowDetailModal(false)}
                                                    title="Close"
                                                >
                                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                                                        <path d="M6 18L18 6M6 6l12 12" />
                                                    </svg>
                                                </button>
                                                <span className="window-dot window-dot--minimize" title="Minimize"></span>
                                                <button 
                                                    className="window-dot window-dot--maximize"
                                                    onClick={() => setIsExpanded(!isExpanded)}
                                                    title={isExpanded ? "Contract" : "Expand"}
                                                >
                                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                                                        {isExpanded ? (
                                                            <path d="M4 14h6v6M20 10h-6V4" />
                                                        ) : (
                                                            <path d="M15 3h6v6M9 21H3v-6" />
                                                        )}
                                                    </svg>
                                                </button>
                                            </div>
                                            <span>Provider Validation Results</span>
                                            <span className="results-window__id">{selectedReport.verification_id}</span>
                                        </div>

                                        <div className="results-window__content">
                                            {/* Provider Summary */}
                                            <div className="provider-summary">
                                                <div className="provider-summary__avatar">👨‍⚕️</div>
                                                <div className="provider-summary__info">
                                                    <h2 className="provider-summary__name">
                                                        {getDisplayName(selectedReport)}
                                                    </h2>
                                                    <p className="provider-summary__specialty">
                                                        {getDisplaySpecialty(selectedReport)}
                                                    </p>
                                                </div>
                                                <div className={`provider-summary__badge ${resultStats.confidence >= 70 ? 'provider-summary__badge--verified' : 'provider-summary__badge--warning'}`}>
                                                    {resultStats.confidence >= 70 ? '✓ Verified' : '⚠ Review Needed'}
                                                </div>
                                            </div>

                                            {/* Stats Dashboard */}
                                            <div className="stats-dashboard">
                                                {/* Chart Card */}
                                                <div className="stats-card stats-card--chart">
                                                    <DonutChart
                                                        verified={resultStats.verified}
                                                        unverified={resultStats.unverified}
                                                        notFound={resultStats.notFound}
                                                        missingDataFound={resultStats.missingDataFound}
                                                    />
                                                </div>

                                                {/* Numbers Card */}
                                                <div className="stats-card stats-card--numbers">
                                                    <h4 className="stats-card__title">Verification Summary</h4>
                                                    <div className="stats-numbers">
                                                        <div className="stat-number stat-number--verified">
                                                            <span className="stat-number__value">{resultStats.verified}</span>
                                                            <span className="stat-number__label">Verified</span>
                                                        </div>
                                                        <div className="stat-number stat-number--mismatch">
                                                            <span className="stat-number__value">{resultStats.unverified}</span>
                                                            <span className="stat-number__label">Mismatched</span>
                                                        </div>
                                                        {(resultStats.missingDataFound || 0) > 0 && (
                                                            <div className="stat-number stat-number--missing-data">
                                                                <span className="stat-number__value">{resultStats.missingDataFound || 0}</span>
                                                                <span className="stat-number__label">Data Found</span>
                                                            </div>
                                                        )}
                                                        <div className="stat-number stat-number--notfound">
                                                            <span className="stat-number__value">{resultStats.notFound}</span>
                                                            <span className="stat-number__label">Not Found</span>
                                                        </div>
                                                        <div className="stat-number stat-number--total">
                                                            <span className="stat-number__value">{resultStats.totalFields}</span>
                                                            <span className="stat-number__label">Total Fields</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Field Confidence Chart */}
                                            <div className="chart-section">
                                                {resultStats.fields && <FieldConfidenceChart fields={resultStats.fields} />}
                                            </div>

                                            {/* Source Distribution & Timeline */}
                                            <div className="insights-grid">
                                                {resultStats.sources?.length > 0 && (
                                                    <SourceDistribution sources={resultStats.sources} />
                                                )}
                                                <VerificationTimeline
                                                    timestamp={selectedReport.created_at}
                                                    verificationId={selectedReport.verification_id}
                                                />
                                            </div>

                                            {/* Detailed Field Comparison */}
                                            <div className="results-grid">
                                                <h3 className="results-grid__title">
                                                    <span className="results-grid__title-icon">📋</span>
                                                    Detailed Field Comparison
                                                </h3>
                                                <div className="results-grid__fields">
                                                    {renderResultField('fullName', convertedData.fullName)}
                                                    {renderResultField('specialty', convertedData.specialty)}
                                                    {renderResultField('address', convertedData.address)}
                                                    {renderResultField('phoneNumber', convertedData.phoneNumber)}
                                                    {renderResultField('licenseNumber', convertedData.licenseNumber)}
                                                    {renderResultField('insuranceNetworks', convertedData.insuranceNetworks)}
                                                    {renderResultField('servicesOffered', convertedData.servicesOffered)}
                                                </div>
                                            </div>

                                            {/* Confidence Section */}
                                            <div className="confidence-section">
                                                <div className="confidence-header">
                                                    <span className="confidence-label">Overall Confidence Score</span>
                                                    <span className={`confidence-value ${resultStats.confidence >= 70 ? 'confidence-value--high' : resultStats.confidence >= 40 ? 'confidence-value--medium' : 'confidence-value--low'}`}>
                                                        {resultStats.confidence}%
                                                    </span>
                                                </div>
                                                <div className="confidence-bar">
                                                    <motion.div
                                                        className={`confidence-fill ${resultStats.confidence >= 70 ? 'confidence-fill--high' : resultStats.confidence >= 40 ? 'confidence-fill--medium' : 'confidence-fill--low'}`}
                                                        initial={{ width: 0 }}
                                                        animate={{ width: `${resultStats.confidence}%` }}
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
                                                Verified on {new Date(selectedReport.created_at).toLocaleString()}
                                            </div>
                                        </div>
                                    </div>

                                    {/* Results Actions */}
                                    {/* Results Actions - Removed */}
                                </motion.div>
                            );
                        })()}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default ReportsPage;