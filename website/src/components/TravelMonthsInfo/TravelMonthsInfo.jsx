import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Button from '../Button/Button.jsx';
import { useUserData } from '../../context/UserDataContext';
import './TravelMonthsInfo.css';

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const YEARS = [2024, 2025, 2026];

// This can be overridden later with the actual API URL
const DEFAULT_API_URL = 'https://api.example.com/submit-preferences';

const TravelMonthsInfo = ({ apiUrl }) => {
  const navigate = useNavigate();
  const { updateUserData } = useUserData();
  const [startMonth, setStartMonth] = useState('');
  const [startYear, setStartYear] = useState(2024);
  const [endMonth, setEndMonth] = useState('');
  const [endYear, setEndYear] = useState(2024);
  const [error, setError] = useState('');

  // Validate selections when they change
  useEffect(() => {
    if (startMonth && endMonth) {
      const startDate = new Date(`${startMonth} 1, ${startYear}`);
      const endDate = new Date(`${endMonth} 1, ${endYear}`);
      
      if (endDate < startDate) {
        setError('End date cannot be before start date');
      } else {
        setError('');
      }
    }
  }, [startMonth, startYear, endMonth, endYear]);

  const getMonthNumber = (monthName) => {
    return MONTHS.indexOf(monthName) + 1;
  };

  const handleContinue = () => {
    if (!startMonth || !endMonth) {
      setError('Please select both start and end months');
      return;
    }
    
    const startDate = new Date(`${startMonth} 1, ${startYear}`);
    const endDate = new Date(`${endMonth} 1, ${endYear}`);
    
    if (endDate < startDate) {
      setError('End date cannot be before start date');
      return;
    }
    
    // Save travel dates to context
    updateUserData({
      "start-month": getMonthNumber(startMonth),
      "start-year": startYear,
      "end-month": getMonthNumber(endMonth),
      "end-year": endYear
    });
    
    // Navigate to results page where the API call will happen
    navigate('/results');
  };

  const handleSkip = () => {
    // Save null travel dates to context
    updateUserData({
      "start-month": null,
      "start-year": null,
      "end-month": null,
      "end-year": null
    });
    
    // Navigate to results page where the API call will happen
    navigate('/results');
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        duration: 1,
        when: "beforeChildren",
        staggerChildren: 0.1
      }
    }
  };

  const titleVariants = {
    hidden: { y: 50, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        type: "spring",
        stiffness: 100,
        damping: 10
      }
    }
  };

  return (
    <motion.div
      className="travel-months-container"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.h1 className="travel-months-heading" variants={titleVariants}>
        When do you want to travel? (roughly)
      </motion.h1>

      <div className="date-pickers-container">
        <div className="date-picker-section">
          <h3 className="date-picker-label">Start Date</h3>
          <div className="date-picker-wrapper">
            <div className="select-wrapper">
              <select 
                className="month-select"
                value={startMonth}
                onChange={(e) => setStartMonth(e.target.value)}
              >
                <option value="">Month</option>
                {MONTHS.map(month => (
                  <option key={month} value={month}>{month}</option>
                ))}
              </select>
            </div>
            <div className="select-wrapper">
              <select 
                className="year-select"
                value={startYear}
                onChange={(e) => setStartYear(parseInt(e.target.value))}
              >
                {YEARS.map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="date-picker-section">
          <h3 className="date-picker-label">End Date</h3>
          <div className="date-picker-wrapper">
            <div className="select-wrapper">
              <select 
                className="month-select"
                value={endMonth}
                onChange={(e) => setEndMonth(e.target.value)}
              >
                <option value="">Month</option>
                {MONTHS.map(month => (
                  <option key={month} value={month}>{month}</option>
                ))}
              </select>
            </div>
            <div className="select-wrapper">
              <select 
                className="year-select"
                value={endYear}
                onChange={(e) => setEndYear(parseInt(e.target.value))}
              >
                {YEARS.map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}
      
      <div className="button-container">
        <Button onClick={handleContinue} className="primary-button">
          Continue
        </Button>
        <Button onClick={handleSkip} className="skip-button">
          <span className="top-text">Skip</span>
          <span className="bottom-text">I'm spontaneous</span>
        </Button>
      </div>
    </motion.div>
  );
};

export default TravelMonthsInfo; 