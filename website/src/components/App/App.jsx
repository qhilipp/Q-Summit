import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Welcome from '../Welcome/Welcome.jsx';
import UniversityInfo from '../UniversityInfo/UniversityInfo.jsx';
import './App.css';

function App() {
  console.log('App component rendered');
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Welcome />} />
        <Route path="/university" element={<UniversityInfo />} />
      </Routes>
    </Router>
  );
}

export default App;
