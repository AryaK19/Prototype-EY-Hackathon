import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import './VerifyPage.css';

const VerifyPage = () => {
    return (
        <div className="verify-page">
            <div className="verify-page__background">
                <div className="verify-page__glow" />
            </div>

            <motion.div
                className="verify-page__content"
                initial={{ opacity: 0, y: 40 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
            >
                <motion.div
                    className="verify-page__icon"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.2, type: 'spring' }}
                >
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
                </motion.div>

                <motion.h1
                    className="verify-page__title"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.3 }}
                >
                    Provider Verification
                </motion.h1>

                <motion.p
                    className="verify-page__subtitle"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.4 }}
                >
                    Upload your provider data and let our AI agents validate, enrich, and
                    update your directory automatically.
                </motion.p>

                <motion.div
                    className="verify-page__card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: 0.5 }}
                >
                    <div className="verify-page__card-header">
                        <span className="verify-page__card-badge">Coming Soon</span>
                    </div>

                    <div className="verify-page__card-content">
                        <div className="verify-page__upload-zone">
                            <div className="verify-page__upload-icon">
                                <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M40 30V38C40 39.0609 39.5786 40.0783 38.8284 40.8284C38.0783 41.5786 37.0609 42 36 42H12C10.9391 42 9.92172 41.5786 9.17157 40.8284C8.42143 40.0783 8 39.0609 8 38V30" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                                    <path d="M32 16L24 8L16 16" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                                    <path d="M24 8V30" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                            </div>
                            <p className="verify-page__upload-text">
                                <span>Drop your provider data here</span>
                                <span className="verify-page__upload-subtext">CSV, Excel, or PDF files supported</span>
                            </p>
                            <button className="btn btn--secondary" disabled>
                                Browse Files
                            </button>
                        </div>

                        <div className="verify-page__features">
                            <div className="verify-page__feature">
                                <span className="verify-page__feature-icon">🔍</span>
                                <span>Auto-validation</span>
                            </div>
                            <div className="verify-page__feature">
                                <span className="verify-page__feature-icon">📊</span>
                                <span>Data enrichment</span>
                            </div>
                            <div className="verify-page__feature">
                                <span className="verify-page__feature-icon">✅</span>
                                <span>Quality scoring</span>
                            </div>
                            <div className="verify-page__feature">
                                <span className="verify-page__feature-icon">📧</span>
                                <span>Email generation</span>
                            </div>
                        </div>
                    </div>
                </motion.div>

                <motion.div
                    className="verify-page__actions"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.5, delay: 0.6 }}
                >
                    <Link to="/" className="btn btn--ghost">
                        ← Back to Home
                    </Link>
                </motion.div>
            </motion.div>
        </div>
    );
};

export default VerifyPage;
