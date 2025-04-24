import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '../Button/Button';
import './Welcome.css';

const Welcome = () => {
  const navigate = useNavigate();

  const vacationPlaces = [
    { name: "New York", image: "https://images.unsplash.com/photo-1496442226666-8d4d0e62e6e9?q=80&w=800&auto=format&fit=crop" },
    { name: "Barcelona", image: "https://images.unsplash.com/photo-1583422409516-2895a77efded?q=80&w=800&auto=format&fit=crop" },
    { name: "Kyoto", image: "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?q=80&w=800&auto=format&fit=crop" },
    { name: "Paris", image: "https://images.unsplash.com/photo-1499856871958-5b9627545d1a?q=80&w=800&auto=format&fit=crop" },
    { name: "Rome", image: "https://images.unsplash.com/photo-1552832230-c0197dd311b5?q=80&w=800&auto=format&fit=crop" },
    { name: "Sydney", image: "https://images.unsplash.com/photo-1506973035872-a4ec16b8e8d9?q=80&w=800&auto=format&fit=crop" },
    { name: "London", image: "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?q=80&w=800&auto=format&fit=crop" },
    { name: "Berlin", image: "https://images.unsplash.com/photo-1560969184-10fe8719e047?q=80&w=800&auto=format&fit=crop" }
  ];

  const [currentImageIndex, setCurrentImageIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentImageIndex(prevIndex => 
        prevIndex === vacationPlaces.length - 1 ? 0 : prevIndex + 1
      );
    }, 3000); // Change image every 3 seconds

    return () => clearInterval(interval);
  }, [vacationPlaces.length]);

  const currentPlace = vacationPlaces[currentImageIndex];

  return (
    <div className="welcome-container">
      
      <div className="content-wrapper">
        <div className="welcome-content">
          <div className="content-inner">
            <h2 className="welcome-title">Want to study abroad?<br/><i>We got you!</i></h2>
            <p className="welcome-description">Our AI-powered tool simplifies planning your semester overseas by helping you find the best-fit universities based on your interests and goals. It provides all the essential details like application deadlines, visa tips, and housing advice in one place, making your journey smart and stress-free.</p>
            <div style={{ marginTop: "20px", marginBottom: "60px" }}>
              <Button onClick={() => navigate('/university')} className="full-width-button" style={{ height: "65px", lineHeight: "65px" }}>
                Let's go
              </Button>
            </div>
          </div>
        </div>
        
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
        
        <nav className="nav-bar">
          <h1 className="nav-title">Study AiBroad</h1>
        </nav>
      </div>
    </div>
  );
};

export default Welcome; 