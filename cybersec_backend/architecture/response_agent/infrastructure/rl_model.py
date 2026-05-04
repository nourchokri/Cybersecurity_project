"""Reinforcement Learning model for decision making."""

from __future__ import annotations
import logging
import pickle
import os
from typing import Dict, List, Tuple
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class SimpleQLearningAgent:
    """Simple Q-Learning agent for action selection."""
    
    def __init__(self, actions: List[str] = None, learning_rate: float = 0.1, 
                 discount_factor: float = 0.95, epsilon: float = 0.1):
        self.actions = actions or ["ALLOW", "MONITOR", "ESCALATE", "BLOCK", "MFA_CHALLENGE"]
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon  # Exploration rate
        
        # Q-table: state_hash -> {action: q_value}
        self.q_table: Dict[str, Dict[str, float]] = {}
        
        # Training history
        self.training_history: List[Dict] = []
    
    def _discretize_state(self, features: Dict[str, float]) -> str:
        """Convert continuous features to discrete state representation with richer context."""
        # Discretize key features into bins
        risk_score = features.get("adjusted_risk_score", 0.0)
        risk_level = features.get("risk_level_numeric", 0.0)  # 0=LOW, 1=MEDIUM, 2=HIGH
        risk_factors_count = features.get("risk_factors_count", 0)
        mitigating_factors_count = features.get("mitigating_factors_count", 0)
        confidence = features.get("confidence_numeric", 0.66)
        
        # Create discrete bins
        risk_bin = int(risk_score * 10)  # 0-10
        level_bin = int(risk_level)  # 0, 1, 2
        rf_bin = min(risk_factors_count, 5)  # Cap at 5
        mf_bin = min(mitigating_factors_count, 5)  # Cap at 5
        conf_bin = int(confidence * 3)  # 0, 1, 2 (low, medium, high)
        
        # Create richer state key with more discriminating features
        # Format: level_riskscore_rf_mf_conf
        # Example: "2_8_4_0_2" = HIGH risk, score 0.8-0.9, 4 risk factors, 0 mitigating, high confidence
        return f"{level_bin}_{risk_bin}_{rf_bin}_{mf_bin}_{conf_bin}"
    
    def get_q_values(self, state_hash: str) -> Dict[str, float]:
        """Get Q-values for a state."""
        if state_hash not in self.q_table:
            # Initialize with small random values
            self.q_table[state_hash] = {action: np.random.uniform(0, 0.1) for action in self.actions}
        return self.q_table[state_hash]
    
    def select_action(self, features: Dict[str, float], explore: bool = False) -> Tuple[str, float]:
        """Select action using epsilon-greedy policy."""
        state_hash = self._discretize_state(features)
        q_values = self.get_q_values(state_hash)
        
        # Epsilon-greedy exploration
        if explore and np.random.random() < self.epsilon:
            action = np.random.choice(self.actions)
            confidence = 0.5
        else:
            # Exploit: choose best action
            action = max(q_values, key=q_values.get)
            max_q = q_values[action]
            # Normalize Q-value to confidence (0-1)
            confidence = min(max(max_q, 0.0), 1.0)
        
        return action, confidence
    
    def update(self, features: Dict[str, float], action: str, reward: float, 
               next_features: Dict[str, float]):
        """Update Q-table based on experience."""
        state_hash = self._discretize_state(features)
        next_state_hash = self._discretize_state(next_features)
        
        q_values = self.get_q_values(state_hash)
        next_q_values = self.get_q_values(next_state_hash)
        
        # Q-learning update
        current_q = q_values[action]
        max_next_q = max(next_q_values.values())
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)
        
        q_values[action] = new_q
        
        # Log training
        self.training_history.append({
            "state": state_hash,
            "action": action,
            "reward": reward,
            "old_q": current_q,
            "new_q": new_q
        })
    
    def save(self, filepath: str):
        """Save model to disk."""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'wb') as f:
                pickle.dump({
                    'q_table': self.q_table,
                    'actions': self.actions,
                    'learning_rate': self.learning_rate,
                    'discount_factor': self.discount_factor,
                    'epsilon': self.epsilon,
                    'training_history': self.training_history
                }, f)
            logger.info(f"RL model saved to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save RL model: {e}")
    
    @classmethod
    def load(cls, filepath: str) -> 'SimpleQLearningAgent':
        """Load model from disk."""
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            
            agent = cls(
                actions=data['actions'],
                learning_rate=data['learning_rate'],
                discount_factor=data['discount_factor'],
                epsilon=data['epsilon']
            )
            agent.q_table = data['q_table']
            agent.training_history = data.get('training_history', [])
            
            logger.info(f"RL model loaded from {filepath}")
            return agent
        except FileNotFoundError:
            logger.warning(f"RL model not found at {filepath}, creating new model")
            return cls(actions=["ALLOW", "MONITOR", "ESCALATE", "BLOCK", "MFA_CHALLENGE"])
        except Exception as e:
            logger.error(f"Failed to load RL model: {e}")
            return cls(actions=["ALLOW", "MONITOR", "ESCALATE", "BLOCK", "MFA_CHALLENGE"])


class RLModelManager:
    """Manages RL model lifecycle."""
    
    def __init__(self, model_path: str = None):
        if model_path is None:
            # Default path in Django project
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            model_path = base_dir / "data" / "rl_models" / "response_agent_rl.pkl"
        
        self.model_path = str(model_path)
        self.agent = SimpleQLearningAgent.load(self.model_path)
    
    def predict(self, features: Dict[str, float]) -> Tuple[str, float]:
        """Predict action for given features."""
        return self.agent.select_action(features, explore=False)
    
    def train(self, features: Dict[str, float], action: str, reward: float, 
              next_features: Dict[str, float]):
        """Train model with new experience."""
        self.agent.update(features, action, reward, next_features)
        self.save()
    
    def save(self):
        """Save model to disk."""
        self.agent.save(self.model_path)
    
    def get_stats(self) -> Dict:
        """Get model statistics."""
        return {
            "q_table_size": len(self.agent.q_table),
            "training_samples": len(self.agent.training_history),
            "actions": self.agent.actions,
            "learning_rate": self.agent.learning_rate,
            "epsilon": self.agent.epsilon
        }
