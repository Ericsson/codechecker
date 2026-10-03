package org.example;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.util.HtmlUtils;

@Controller
public class UserProfileController {

    // Display user profile with custom message
    @GetMapping("/profile/display")
    @ResponseBody
    public String displayUserProfile(
            @RequestParam(defaultValue = "Welcome") String message) {
        // Direct output without escaping
        return "<html><body><h1>Profile Message: " + message + "</h1></body></html>";
    }
}
