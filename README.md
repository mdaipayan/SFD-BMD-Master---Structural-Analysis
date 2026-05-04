# 🏗️ SFD & BMD Master

An interactive **Streamlit** web application for teaching and learning **Shear Force Diagrams (SFD)** and **Bending Moment Diagrams (BMD)** in structural analysis.

## 🌟 Features

### 📊 Interactive Analysis
- **Real-time beam configuration** with customizable supports, loads, and moments
- **Automatic calculation** of support reactions using static equilibrium equations
- **Dynamic plotting** of Loading Diagram, SFD, and BMD
- **Step-by-step solutions** showing the complete mathematical derivation

### 📚 Educational Content
- **Theory section** with fundamental equations and sign conventions
- **Load-Shear-Moment relationships** explained with differential equations
- **Common beam formulas** for quick reference
- **Sign convention clarity** for positive/negative shear and moment

### 🧮 Quick Calculator
- Pre-configured calculators for standard beam problems:
  - Simply supported beam with point load
  - Simply supported beam with UDL
  - Cantilever with end point load
  - Cantilever with UDL

### 📖 Worked Examples
- Detailed step-by-step solutions for common problems
- Visual diagrams with mathematical explanations
- Verification of results using equilibrium checks

## 🚀 Deployment

### Option 1: Streamlit Cloud (Recommended)
1. Fork this repository to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account and select this repository
4. Click "Deploy"

### Option 2: Local Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/sfd-bmd-master.git
cd sfd-bmd-master

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

### Option 3: Docker
```bash
docker build -t sfd-bmd-master .
docker run -p 8501:8501 sfd-bmd-master
```

## 📋 Requirements

- Python 3.8+
- Streamlit 1.28+
- NumPy 1.24+
- Matplotlib 3.7+

## 🎯 Learning Objectives

After using this app, students will be able to:

1. **Understand static equilibrium** and apply ΣF = 0, ΣM = 0
2. **Calculate support reactions** for various beam configurations
3. **Construct Shear Force Diagrams** using the method of sections
4. **Construct Bending Moment Diagrams** by integrating shear or using moment equilibrium
5. **Identify critical points** where maximum shear and moment occur
6. **Apply differential relationships**: dV/dx = -w and dM/dx = V

## 🏛️ Beam Types Supported

- ✅ Simply Supported Beams
- ✅ Cantilever Beams
- ✅ Overhanging Beams
- ✅ Custom multi-support configurations

## ⚖️ Load Types Supported

- ✅ Concentrated Point Loads
- ✅ Uniformly Distributed Loads (UDL)
- ✅ Trapezoidal Distributed Loads
- ✅ Concentrated Moments/Couples

## 📐 Mathematical Foundation

### Static Equilibrium Equations
```
ΣFx = 0
ΣFy = 0
ΣM = 0
```

### Differential Relationships
```
dV/dx = -w(x)
dM/dx = V(x)
d²M/dx² = -w(x)
```

### Integration Relationships
```
V = ∫(-w)dx + C₁
M = ∫V dx + C₂
```

## 🖥️ Application Structure

```
sfd-bmd-master/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── .gitignore         # Git ignore file
└── assets/            # Images and documentation (optional)
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Visualization powered by [Matplotlib](https://matplotlib.org/)
- Numerical computing with [NumPy](https://numpy.org/)

## 📧 Contact

For questions or suggestions, please open an issue on GitHub.

---

**Happy Learning! 🎓**
