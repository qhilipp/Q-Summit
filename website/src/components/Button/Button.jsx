import { motion } from 'framer-motion';
import './Button.css';

const Button = ({ children, onClick, className = '' }) => {
  return (
    <motion.button
      className={`welcome-button ${className}`}
      onClick={onClick}
    >
      {children}
    </motion.button>
  );
};

export default Button; 