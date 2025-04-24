import React, { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useUserData } from '../../context/UserDataContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import './UniversityPage.css';

const UniversityPage = () => {
  const { id } = useParams();
  const { userData } = useUserData();
  const [plan, setPlan] = useState(null);
  const [isLoadingPlan, setIsLoadingPlan] = useState(false);
  const [error, setError] = useState(null);
  const requestMade = useRef(false);

  useEffect(() => {
    const fetchApplicationPlan = async () => {
      if (requestMade.current) return;
      requestMade.current = true;

      //if (!userData.university || !userData.major) return;
      console.log("Fetching application plan");
      setIsLoadingPlan(true);
      setError(null);
      
      try {
        const myHeaders = new Headers();
        myHeaders.append("Content-Type", "application/json");

        const raw = JSON.stringify({
          "home_university": "Muenster",//userData.university,
          "target_university": "UCSB",//decodeURIComponent(id),
          "major": "Computer Science"//userData.major
        });

        const requestOptions = {
          method: "POST",
          headers: myHeaders,
          body: raw,
          redirect: "follow"
        };
        console.log(requestOptions);
        const response = await fetch("http://localhost:8000/application_plan", requestOptions);
        console.log("Got it!");
        const result = await response.json();
        console.log(result);
        setPlan(result.plan);
      } catch (error) {
        console.error('Error fetching application plan:', error);
        setError('Failed to fetch your application plan. Please try again later.');
      } finally {
        setIsLoadingPlan(false);
      }
    };

    fetchApplicationPlan();

    // Cleanup function to reset the ref when component unmounts
    return () => {
      requestMade.current = false;
    };
  }, [userData.university, userData.major, id]);

  return (
    <motion.div 
      className="university-page-container"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
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
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
              components={{
                // Add custom components for better rendering
                h1: ({node, ...props}) => <h1 style={{color: '#ffffff'}} {...props} />,
                h2: ({node, ...props}) => <h2 style={{color: '#ffffff'}} {...props} />,
                h3: ({node, ...props}) => <h3 style={{color: '#ffffff'}} {...props} />,
                p: ({node, ...props}) => <p style={{color: '#ffffff', lineHeight: '1.6'}} {...props} />,
                ul: ({node, ...props}) => <ul style={{color: '#ffffff', marginLeft: '1.5rem'}} {...props} />,
                ol: ({node, ...props}) => <ol style={{color: '#ffffff', marginLeft: '1.5rem'}} {...props} />,
                li: ({node, ...props}) => <li style={{color: '#ffffff', marginBottom: '0.5rem'}} {...props} />,
                a: ({node, ...props}) => <a style={{color: '#64b5f6'}} {...props} />,
                code: ({node, inline, ...props}) => (
                  inline ? 
                    <code style={{background: 'rgba(255, 255, 255, 0.1)', padding: '0.2em 0.4em', borderRadius: '3px'}} {...props} /> :
                    <code style={{display: 'block', background: 'rgba(0, 0, 0, 0.2)', padding: '1em', borderRadius: '4px', overflowX: 'auto'}} {...props} />
                )
              }}
            >
              {plan}
            </ReactMarkdown>
          </div>
        ) : null}
      </div>
    </motion.div>
  );
};

export default UniversityPage; 