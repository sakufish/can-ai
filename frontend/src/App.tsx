import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Map from './pages/Map';

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/temp" element={<Home />} />
        <Route path="/" element={<Map />} />
      </Routes>
    </Router>
  );
};

export default App;
