import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../Button/Button.jsx';
import './Welcome.css';

const Welcome = () => {
  const navigate = useNavigate();

  const vacationPlaces = [
    { name: "New York", image: "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?q=80&w=800&auto=format&fit=crop" },
    { name: "Santa Barbara", image: "https://mediaim.expedia.com/destination/9/361b9dfb25a3b8d1e66a7c567ffc2602.jpg" },
    { name: "Barcelona", image: "https://images.unsplash.com/photo-1583422409516-2895a77efded?q=80&w=800&auto=format&fit=crop" },
    { name: "Kyoto", image: "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?q=80&w=800&auto=format&fit=crop" },
    { name: "Paris", image: "https://images.unsplash.com/photo-1499856871958-5b9627545d1a?q=80&w=800&auto=format&fit=crop" },
    { name: "Rome", image: "https://images.unsplash.com/photo-1552832230-c0197dd311b5?q=80&w=800&auto=format&fit=crop" },
    { name: "Sydney", image: "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?q=80&w=800&auto=format&fit=crop" },
    { name: "London", image: "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?q=80&w=800&auto=format&fit=crop" },
    { name: "Berlin", image: "https://images.unsplash.com/photo-1560969184-10fe8719e047?q=80&w=800&auto=format&fit=crop" }
  ];

  const [currentImageIndex, setCurrentImageIndex] = useState(0);

  const handleMouseMove = useCallback((e) => {
    const container = document.querySelector('.slideshow-image-container');
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    // Calculate distance from center as a percentage (-50 to 50)
    const rotateY = -((e.clientX - centerX) / rect.width) * 4;
    const rotateX = ((e.clientY - centerY) / rect.height) * 4;
    
    container.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [handleMouseMove]);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentImageIndex(prevIndex => 
        prevIndex === vacationPlaces.length - 1 ? 0 : prevIndex + 1
      );
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const currentPlace = vacationPlaces[currentImageIndex];

  return (
    <div className="welcome-container">
      <nav className="nav-bar">
        <h1 className="nav-title">Bring me <span>Ai</span>Broad</h1>
      </nav>

      <div className="content-wrapper">
        <div className="welcome-content">
          <div className="content-inner">
            <h2 className="welcome-title">Want to study abroad?<br/><i>We got you!</i></h2>
            <p className="welcome-description">
              Studying abroad can be a daunting task, but we're here to help. Our AI-Multi-Agent System will help you find the perfect university for you. And to top it off, it'll also help you with the organization! For free!
            </p>
            <Button onClick={() => navigate('/university')} className="select-button">
              Let's go
            </Button>
          </div>
        </div>

        <div className="right-section">
          <div className="slideshow-container">
            <div className="slideshow-image-container">
              <img 
                src={currentPlace.image} 
                alt={currentPlace.name} 
                className="slideshow-image"
              />
              <div className="slideshow-caption">{currentPlace.name}</div>
            </div>
            <div className="slideshow-dots">
              {vacationPlaces.map((_, index) => (
                <span 
                  key={index} 
                  className={`slideshow-dot ${index === currentImageIndex ? 'active' : ''}`}
                  onClick={() => setCurrentImageIndex(index)}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Welcome; 