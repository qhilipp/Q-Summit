import React from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../Button/Button';
import './Welcome.css';

const Welcome = () => {
  const navigate = useNavigate();

  return (
    <div className="welcome-container">
  <div className="content-wrapper">
    <div className="welcome-content">
      <div className="content-inner">
        <h2 className="welcome-title">Want to study abroad?<br/><i>We got you!</i></h2>
        <p className="welcome-description">Planning your semester abroad can feel overwhelming – but it doesn't have to be. Our AI-powered tool helps you find the perfect university match in just a few clicks. Answer a few quick questions, and we'll suggest study destinations tailored to your interests, field, and goals. Whether you're dreaming of big cities, beach towns, or top-ranked programs, we've got options. No more hours of research – get all the key info you need in one place. From application deadlines to housing tips, we've got your back. Start exploring your global adventure today – it's that easy.</p>
        <Button onClick={() => navigate('/university')} className="full-width-button">
          Let's go
        </Button>
      </div>
    </div>
    
    <nav className="nav-bar">
      <h1 className="nav-title">Study AIbroad</h1>
    </nav>
  </div>
</div>
  );
};

export default Welcome; 