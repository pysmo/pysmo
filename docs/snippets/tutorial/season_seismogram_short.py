@dataclass
class SeasonSeismogram(SeismogramEndtimeMixin):  # (1)!
    begin_time: Timestamp
    delta: Timedelta = Timedelta(seconds=0.01)
    data: np.ndarray = field(default_factory=lambda: np.array([]))
    season: Season = Season.SUMMER
