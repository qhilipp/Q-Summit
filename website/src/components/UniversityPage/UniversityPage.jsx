import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useUserData } from '../../context/UserDataContext';
import ReactMarkdown from 'react-markdown';
import './UniversityPage.css';

const UniversityPage = () => {
  const { id } = useParams();
  const { userData } = useUserData();
  const [plan, setPlan] = useState(null);
  const [isLoadingPlan, setIsLoadingPlan] = useState(false);
  const [error, setError] = useState(null);

  // Debug log to check userData
  useEffect(() => {
    console.log('Current userData:', userData);
  }, [userData]);

  useEffect(() => {
    const fetchApplicationPlan = async () => {
      if (!userData.university || !userData.major) return;
      
      setIsLoadingPlan(true);
      setError(null);
      
      try {
        const myHeaders = new Headers();
        myHeaders.append("Content-Type", "application/json");

        const raw = JSON.stringify({
          "home_university": userData.university,
          "target_university": decodeURIComponent(id),
          "major": userData.major
        });

        const requestOptions = {
          method: "POST",
          headers: myHeaders,
          body: raw,
          redirect: "follow"
        };

        const response = await fetch("http://localhost:8000/application_plan", requestOptions);
        const result = await response.text();
        setPlan(result);
      } catch (error) {
        console.error('Error fetching application plan:', error);
        setError('Failed to fetch your application plan. Please try again later.');
      } finally {
        setIsLoadingPlan(false);
      }
    };

    fetchApplicationPlan();
  }, [userData.university, userData.major, id]);

  return (
    <motion.div 
      className="university-page-container"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <div className="user-info-section">
        <h2>Your Information</h2>
        <div className="info-item">
          <span className="info-label">Home University:</span>
          <span className="info-value">
            {userData.university || 'Not specified'} 
            {!userData.university && <span className="debug-info">(Check if data was saved in UniversityInfo component)</span>}
          </span>
        </div>
        <div className="info-item">
          <span className="info-label">Major:</span>
          <span className="info-value">
            {userData.major || 'Not specified'}
            {!userData.major && <span className="debug-info">(Check if data was saved in UniversityInfo component)</span>}
          </span>
        </div>
        <div className="info-item debug-row">
          <span className="info-label">Context Data:</span>
          <span className="info-value debug-data">{JSON.stringify(userData, null, 2)}</span>
        </div>
      </div>
      <h1 className="university-page-title">
        {decodeURIComponent(id)}
      </h1>

      <div className="plan-section">
        {isLoadingPlan ? (
          <div className="plan-loading">
            <div className="plan-spinner"></div>
            <p>Crafting your plan...</p>
          </div>
        ) : error ? (
          <div className="plan-error">
            {error}
          </div>
        ) : plan ? (
          <div className="plan-content">
            <ReactMarkdown>{plan}</ReactMarkdown>
          </div>
        ) : null}
      </div>
    </motion.div>
  );
};

export default UniversityPage; 