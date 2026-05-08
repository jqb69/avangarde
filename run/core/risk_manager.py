# core/risk_manager.py

class RiskManager:
    def __init__(self, config):
        self.max_drawdown = config.get('max_drawdown', 0.10)
        self.max_position_size = config.get('max_size', 1.0) # Lots

    def validate_trade(self, decision: Dict, current_exposure: float) -> bool:
        # 1. Kill if confidence is too low
        if decision.get('confidence', 0) < 0.75:
            return False
        
        # 2. Kill if we are over-leveraged
        if current_exposure > self.max_position_size:
            return False
            
        return True
