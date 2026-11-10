package com.f1dataplatform.backend.config;

import com.f1dataplatform.backend.error.JsonErrorReportValve;
import org.springframework.boot.web.embedded.tomcat.TomcatServletWebServerFactory;
import org.springframework.boot.web.server.WebServerFactoryCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;

/** Registra la valvola che dà un corpo JSON agli errori respinti da Tomcat prima di Spring. */
@Configuration
public class TomcatErrorConfig {

    /**
     * Ultimo tra i personalizzatori: la valvola finisce dopo quella predefinita di Spring Boot nella
     * catena dell'host, quindi è la prima a vedere la risposta d'errore e a scriverne il corpo.
     */
    @Bean
    @Order(Ordered.LOWEST_PRECEDENCE)
    WebServerFactoryCustomizer<TomcatServletWebServerFactory> jsonErrorReportValve() {
        return factory -> factory.addContextCustomizers(
                context -> context.getParent().getPipeline().addValve(new JsonErrorReportValve()));
    }
}
