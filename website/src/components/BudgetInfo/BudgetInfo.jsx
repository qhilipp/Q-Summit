import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import Button from '../Button/Button.jsx';
import { useUserData } from '../../context/UserDataContext';
import './BudgetInfo.css';

const BudgetInfo = () => {
  const navigate = useNavigate();
  const { updateUserData } = useUserData();
  const [budget, setBudget] = useState('');
  const [error, setError] = useState('');

  const handleBudgetChange = (e) => {
    const value = e.target.value;
    // Allow only numbers and commas
    if (value === '' || /^[0-9,]+$/.test(value)) {
      setBudget(value);
      if (error) setError('');
    }
  };

  const handleContinue = () => {
    if (!budget) {
      setError('Please enter your budget or click Skip');
      return;
    }
    
    // Remove commas and check if it's a valid number
    const budgetNumber = Number(budget.replace(/,/g, ''));
    if (isNaN(budgetNumber) || budgetNumber <= 0) {
      setError('Please enter a valid budget amount');
      return;
    }
    
    // Save budget to context
    updateUserData({ budget: budgetNumber });
    
    // Proceed to next page
    navigate('/travel-months');
  };

  const handleSkip = () => {
    // Save null budget to context
    updateUserData({ budget: null });
    
    // Proceed to next page without budget
    navigate('/travel-months');
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
      className="budget-container"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.h1 className="budget-heading" variants={titleVariants}>
        What is your monthly budget?
      </motion.h1>

      <div className="input-container">
        <div className="input-wrapper">
          <div className="currency-input-container">
            <span className="currency-symbol">€</span>
            <input 
              type="text" 
              placeholder="Enter your monthly budget" 
              className={`info-input currency-input ${error ? 'error' : ''}`}
              value={budget}
              onChange={handleBudgetChange}
            />
          </div>
          {error && <div className="error-message">{error}</div>}
        </div>
      </div>
      
      <div className="button-container">
        <Button onClick={handleContinue} className="primary-button">
          Continue
        </Button>
        <Button onClick={handleSkip} className="skip-button">
          <span class="top-text">Skip</span>
          <span class="bottom-text">I don't care about $$$</span>
        </Button>
      </div>
    </motion.div>
  );
};

export default BudgetInfo; 