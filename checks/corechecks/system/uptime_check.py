import uptime

from checks import AgentCheck


class UptimeCheck(AgentCheck):
    def check(self, instance):
        self.gauge("system.uptime", uptime.uptime())
